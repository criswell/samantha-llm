# Substrate-Native Auto-Memory Disable

**Date**: 2026-07-13
**Purpose**: Keep the cerebrum the sole authoritative memory in session by
disabling substrate-native auto-memory when samantha-llm launches an agent.

## Motivation

Some agent substrates maintain their own native auto-memory subsystem that is
injected into the session separately from the cerebrum (e.g. Claude Code's
`~/.claude/projects/<project>/memory/` auto-memory, ~10KB injected into the
system prompt each session). That memory overlaps with the cerebrum but is
maintained by a different process and in a different format, so the two diverge
over time — a dual-memory divergence problem.

## Changes

### New module: `agent_env.py`

Standalone, importable-by-tests module that builds the child process
environment:

- `native_auto_memory_disable_env(command) -> dict` — maps the agent's
  substrate (detected from the leading command token) to the env vars that
  disable its native auto-memory. Currently maps `claude` →
  `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`; other substrates return `{}`.
  Generalizable — add new substrates to `_SUBSTRATE_DISABLE_ENV` as their
  disable env vars become known.
- `build_child_env(agent_config, base_env=None) -> dict` — layers
  `base_env` (defaults to a copy of `os.environ`) + the substrate
  auto-memory disable (default-on) + a per-agent `env` dict (applied last,
  so explicit per-agent values win). Never mutates the base env.

### New tests: `test_agent_env.py`

15 unittest cases covering: claude detection (with/without flags, leading
whitespace, path-qualified), non-claude substrates returning empty, base-env
inheritance, default-on, opt-out via `disable_native_auto_memory: false`,
per-agent `env` merge and override, and base-env non-mutation.

### `samantha-llm` launcher wiring

- `_load_agent_env_module(repo_path)` helper loads `agent_env.py` by path
  (same pattern as `transcript_capture`), so it works regardless of how
  samantha-llm is invoked.
- `cmd_start` builds `child_env` via `build_child_env(agent_config)` and
  passes `env=child_env` to every launch path: `run_agent_with_recording_shell`
  and both non-recording fallbacks (Unix and Windows).
- `run_agent_with_recording_shell` accepts an `env` parameter and passes it
  to all three of its `subprocess.run` sites (Windows PowerShell, Unix
  `script`, and the no-`script` fallback).
- `cmd_agents` shows each agent's native auto-memory status
  (disabled / enabled (opt-out) / n/a).
- `cmd_setup` notes the disable for the Claude Code choice.

## Behavior

- **Default-on, in code** — existing installs get the disable without a config
  migration. A user's already-configured `claude` agent is auto-disabled on the
  next `samantha-llm start`.
- **Opt-out** — set `disable_native_auto_memory: false` on an agent config to
  re-enable the substrate's native auto-memory for that agent.
- **Per-agent `env` dict** — general escape hatch for any other env vars a
  substrate may need; applied last so it can override the disable.
- **Bare substrate invocations** (not launched through samantha-llm) keep their
  native auto-memory as an escape hatch.

## Out of Scope (Follow-ups)

- A convenience command/flag to *also* write the disable into a persistent
  location (Claude Code `settings.json` `env` or `~/.zshenv`) for users who
  want bare-substrate coverage too. Not needed for the launch-env behavior and
  intentionally not forced on users.

## Docs

README updated with a "Single Authoritative Memory" section describing the
behavior, the opt-out, and the bare-substrate escape hatch.
