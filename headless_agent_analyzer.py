#!/usr/bin/env python3
"""
Config-driven headless analyzer backend.

Reuses the agent already configured in samantha-llm (the `agents` section of
config.json) to run subconscious chunk analysis, instead of requiring one
specific CLI. The agent that drives interactive sessions can drive background
analysis too, through its non-interactive mode.

Built-in handling:
    claude    delegates to claude_analyzer (system-prompt file, stdin payload,
              gateway token remap)
    codex     delegates to codex_analyzer when the Codex CLI is available
    opencode  `opencode run`, full input on stdin, analysis prompt prepended

Any other agent can be wired without code changes via config.json:

    "subconscious": {
        "analyzer_agent": "myagent",
        "headless_commands": {
            "myagent": {
                "command": "myagent --headless",
                "prompt_mode": "prepend"
            }
        }
    }

`command` is run through the shell with the payload on stdin (argv passing is
avoided: Linux MAX_ARG_STRLEN caps a single argument at 128 KiB, below the
150k-char chunk size). `prompt_mode: prepend` places the analysis prompt above
the payload for CLIs without a system-prompt flag; `none` assumes the CLI
supplies its own instructions.

Timeout handling: each invocation runs in its own session (start_new_session)
so a timeout can kill the whole process tree, not just the shell. The default
cap is 300 seconds; set `subconscious.headless_timeout_seconds` in config.json
to raise it (minimum 30). The 2026-11-13/14 chunk-retry incident (a hung
abacusai server connection stalling an unattended retry for hours at a time)
was the prompt for both: subprocess.run's plain timeout left orphaned pipe
holders alive, and 300s was tight for the largest chunks.
"""

import json
import os
import shlex
import shutil
import signal
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from conversation_analyzer import AnalysisParser, AnalysisResult

DEFAULT_CONFIG_PATH = Path.home() / '.config' / 'samantha-llm' / 'config.json'

PROMPT_SEPARATOR = "\n\n-----\n\nANALYSIS TARGET (parsed conversation) -----\n\n"
READ_CHUNK = 1024 * 1024
DEFAULT_TIMEOUT_SECONDS = 300


def _resolve_timeout(sub_config: dict) -> int:
    """Headless timeout in seconds: subconscious.headless_timeout_seconds.

    Minimum 30s; falls back to the 300s default on any bad value.
    """
    try:
        return max(30, int(sub_config.get('headless_timeout_seconds', DEFAULT_TIMEOUT_SECONDS)))
    except (TypeError, ValueError):
        return DEFAULT_TIMEOUT_SECONDS


@dataclass
class HeadlessSpec:
    """How to drive one agent CLI in non-interactive mode."""
    command: str                      # shell command line; payload arrives on stdin
    prompt_mode: str = 'prepend'      # 'prepend' | 'none'
    input: str = 'stdin'              # only 'stdin' is supported (argv size limits)
    shell: bool = True                # run command via shell (config-provided strings)


# Built-in specs. claude/codex are handled by delegation in create_agent_analyzer
# (their dedicated analyzers carry env/auth handling worth preserving).
BUILTIN_SPECS = {
    'opencode': HeadlessSpec(command='opencode run'),
}


def load_subconscious_config(config_path: Optional[Path] = None) -> dict:
    """Load the `subconscious` section of the user config ({} on any failure)."""
    if config_path is None:
        config_path = Path(os.environ.get(
            'SAMANTHA_LLM_CONFIG', str(DEFAULT_CONFIG_PATH)
        ))
    try:
        with open(config_path, encoding='utf-8') as f:
            data = json.load(f)
        section = data.get('subconscious', {})
        return section if isinstance(section, dict) else {}
    except Exception:
        return {}


def resolve_spec(agent_name: str, sub_config: dict) -> Optional[HeadlessSpec]:
    """Resolve a headless spec: config headless_commands first, then built-ins."""
    custom = sub_config.get('headless_commands', {})
    entry = custom.get(agent_name) if isinstance(custom, dict) else None
    if isinstance(entry, dict) and entry.get('command'):
        return HeadlessSpec(
            command=str(entry['command']),
            prompt_mode=str(entry.get('prompt_mode', 'prepend')),
            input=str(entry.get('input', 'stdin')),
        )
    return BUILTIN_SPECS.get(agent_name)


def agent_supported(agent_name: str, sub_config: Optional[dict] = None) -> bool:
    """True when a headless invocation exists for this agent name."""
    sub = sub_config if sub_config is not None else load_subconscious_config()
    if agent_name in ('claude', 'codex'):
        return True  # delegated to their dedicated analyzer modules
    return resolve_spec(agent_name, sub) is not None


def _fmt_timeout(seconds: int) -> str:
    """Human-readable timeout: '5 minutes' when even, '45 seconds' otherwise."""
    if seconds >= 60 and seconds % 60 == 0:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    return f"{seconds} seconds"


def _run_headless(command: str, stdin_text: str, timeout: int) -> subprocess.CompletedProcess:
    """Run one headless CLI invocation, killing the whole process group on timeout.

    Two failure modes to defend against, both seen in the 2026-11-13/14 stall:

    1. subprocess.run's timeout kills only the direct child (the shell), leaving
       CLI-spawned helpers alive holding the stdin pipe. The parent CLI never
       notices its server is gone and an unattended retry sits for hours
       (server hangs of 128 and 308 minutes in session 20261113_172955).
    2. Even with a process-group kill, a grandchild that called setsid() itself
       (daemonized) escapes the group. So after TimeoutExpired, sweep remaining
       descendants of the child pid as a fallback.

    We manage Popen directly (rather than subprocess.run) to hold the child's
    pid for that sweep. The cap is enforced in all paths: communicate() gets
    the timeout, then killpg, then the descendant sweep, then re-raise.
    """
    try:
        proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True,
            start_new_session=True,
        )
    except FileNotFoundError:
        # shell=True routes through /bin/sh, so this only fires if the shell
        # itself is missing; preserve the historical FileNotFoundError contract.
        raise
    try:
        stdout, stderr = proc.communicate(input=stdin_text, timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_process_tree(proc.pid)
        # Reap; output is irrelevant on the failure path.
        try:
            proc.communicate(timeout=10)
        except Exception:
            pass
        raise
    returncode = proc.returncode
    if returncode != 0:
        raise subprocess.CalledProcessError(returncode, command, output=stdout,
                                            stderr=stderr)
    return subprocess.CompletedProcess(command, returncode, stdout, stderr)


def _kill_process_tree(child_pid: int) -> None:
    """Kill the child's whole process group, then any surviving descendants.

    The group kill (SIGKILL) handles normal trees; the /proc walk catches
    daemonized grandchildren that escaped into their own session.
    """
    import errno
    import time as _time

    try:
        os.killpg(os.getpgid(child_pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass

    # Daemonized escapees: walk /proc for descendants of child_pid.
    deadline = _time.monotonic() + 5
    while _time.monotonic() < deadline:
        try:
            os.kill(child_pid, 0)  # child itself still around?
        except ProcessLookupError:
            child_gone = True
        else:
            child_gone = False
        descendants = _descendants_of(child_pid)
        if child_gone and not descendants:
            return
        for pid in descendants:
            try:
                os.kill(pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
        _time.sleep(0.2)
    # Best effort: never block the retry loop past this window.


def _descendants_of(root_pid: int) -> list:
    """Return live pids whose /proc/<pid>/status PPid chain reaches root_pid."""
    descendants = []
    try:
        entries = [p for p in os.listdir('/proc') if p.isdigit()]
    except OSError:
        return descendants
    # Breadth-first over ppid links; /proc order is arbitrary, iterate to fixpoint.
    known = {root_pid}
    changed = True
    while changed:
        changed = False
        for entry in entries:
            pid = int(entry)
            if pid in known:
                continue
            try:
                with open(f'/proc/{entry}/status', encoding='ascii', errors='replace') as f:
                    for line in f:
                        if line.startswith('PPid:'):
                            ppid = int(line.split()[1])
                            if ppid in known:
                                known.add(pid)
                                descendants.append(pid)
                                changed = True
                            break
            except (OSError, ValueError):
                continue
    return descendants


class HeadlessAgentAnalyzer:
    """Runs chunk analysis through a configured agent's headless CLI."""

    def __init__(self, prompt_path: Path, spec: HeadlessSpec,
                 output_dir: Optional[Path] = None, agent_name: str = 'headless',
                 timeout: int = DEFAULT_TIMEOUT_SECONDS):
        self.prompt_path = Path(prompt_path)
        self.spec = spec
        self.output_dir = Path(output_dir) if output_dir else None
        if self.output_dir:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        self.agent_name = agent_name
        self.timeout = timeout

    def _read(self, path: Path) -> str:
        with open(path, encoding='utf-8', errors='replace') as f:
            return f.read(READ_CHUNK)

    def analyze(self, recording_path: Path) -> AnalysisResult:
        if self.spec.input != 'stdin':
            raise RuntimeError(
                f"Unsupported input mode '{self.spec.input}' for agent "
                f"'{self.agent_name}' (only 'stdin' is supported)"
            )

        prompt_text = self._read(self.prompt_path)
        payload_text = self._read(recording_path)

        if self.spec.prompt_mode == 'prepend':
            stdin_text = prompt_text + PROMPT_SEPARATOR + payload_text
        else:
            stdin_text = payload_text

        try:
            result = _run_headless(self.spec.command, stdin_text, self.timeout)
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"Agent '{self.agent_name}' analysis timed out after "
                f"{_fmt_timeout(self.timeout)}"
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Agent '{self.agent_name}' invocation failed with exit code "
                f"{e.returncode}\nCommand: {self.spec.command}\n"
                f"STDERR:\n{e.stderr[:2000]}"
            )
        except FileNotFoundError:
            raise RuntimeError(
                f"Agent '{self.agent_name}' command not found: "
                f"'{shlex.split(self.spec.command)[0] if self.spec.command else ''}'"
            )

        # Save raw output if output directory is configured. Matches the
        # claude_analyzer/codex_analyzer convention: the caller passes a
        # parsed file named parsed_<id>.txt (chunked runs: parsed_<sid>_chunkN.txt),
        # and the raw LLM output lands next to it as analysis_<id>.md. Without
        # this, the worker's combine step has no chunk files to merge into
        # analysis_<sid>_full.md (written empty) and procedural extraction
        # (Phase 3.5) never fires for headless agents.
        if self.output_dir:
            output_file = self.output_dir / f'analysis_{recording_path.stem.replace("parsed_", "")}.md'
            output_file.write_text(result.stdout)

        return AnalysisParser.parse(result.stdout)

    def run_raw(self, payload_path: Path) -> str:
        """Run the configured agent headlessly and return the RAW stdout text.

        Unlike analyze(), no prompt prepend logic difference: the prompt is
        still prepended per spec, but the output is returned unparsed. Used
        by procedural_extractor, whose LLM output contract is JSON (parsed
        by its own _parse_output), not the AnalysisResult shape.
        """
        prompt_text = self._read(self.prompt_path)
        payload_text = self._read(payload_path)

        if self.spec.prompt_mode == 'prepend':
            stdin_text = prompt_text + PROMPT_SEPARATOR + payload_text
        else:
            stdin_text = payload_text

        try:
            result = _run_headless(self.spec.command, stdin_text, self.timeout)
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"Agent '{self.agent_name}' extraction timed out after "
                f"{_fmt_timeout(self.timeout)}"
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Agent '{self.agent_name}' invocation failed with exit code "
                f"{e.returncode}\nCommand: {self.spec.command}\n"
                f"STDERR:\n{e.stderr[:2000]}"
            )
        except FileNotFoundError:
            raise RuntimeError(
                f"Agent '{self.agent_name}' command not found: "
                f"'{shlex.split(self.spec.command)[0] if self.spec.command else ''}'"
            )

        return result.stdout


def create_agent_analyzer(prompt_path: Path, output_dir: Optional[Path] = None,
                          agent_name: Optional[str] = None,
                          config_path: Optional[Path] = None):
    """
    Create an analyzer for a named agent.

    Resolution order for agent_name:
      1. explicit argument
      2. config subconscious.analyzer_agent ('auto' or unset -> default_agent)
      3. 'claude' if a claude CLI exists

    claude/codex delegate to their dedicated analyzer modules; everything else
    resolves through headless specs (built-in or config headless_commands).

    Returns (analyzer, resolved_agent_name) or (None, None) when nothing
    applicable is configured; raises RuntimeError only on an explicit,
    unsupported request.
    """
    sub = load_subconscious_config(config_path)

    requested = agent_name or sub.get('analyzer_agent') or 'auto'
    explicit = requested not in ('', 'auto', None)

    if not explicit or requested == 'auto':
        configured_default = None
        try:
            cfg_path = config_path or Path(os.environ.get(
                'SAMANTHA_LLM_CONFIG', str(DEFAULT_CONFIG_PATH)))
            with open(cfg_path, encoding='utf-8') as f:
                configured_default = json.load(f).get('default_agent')
        except Exception:
            pass
        requested = configured_default or 'claude'

    name = str(requested).strip().lower().replace('_', '-')

    if name == 'claude':
        import claude_analyzer
        return claude_analyzer.create_analyzer(prompt_path, output_dir=output_dir), 'claude'

    if name in ('codex', 'codex-cli'):
        import analyzer_factory
        if analyzer_factory.codex_available():
            return analyzer_factory.create_named_analyzer('codex', prompt_path, output_dir), 'codex'
        if explicit:
            raise RuntimeError("Codex CLI not available for requested analyzer")
        return None, None

    spec = resolve_spec(name, sub)
    if spec is None:
        if explicit:
            raise RuntimeError(
                f"No headless invocation for agent '{name}'. Add one under "
                f"subconscious.headless_commands in config.json"
            )
        return None, None

    if shutil.which(shlex.split(spec.command)[0]) is None:
        if explicit:
            raise RuntimeError(
                f"Agent '{name}' command not found in PATH: "
                f"'{shlex.split(spec.command)[0]}'"
            )
        return None, None

    return HeadlessAgentAnalyzer(prompt_path, spec, output_dir=output_dir,
                                 agent_name=name,
                                 timeout=_resolve_timeout(sub)), name
