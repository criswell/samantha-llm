#!/usr/bin/env python3
"""
Child environment builder for samantha-llm agent launches.

Samantha-llm treats the cerebrum (`.ai-cerebrum/`) as the authoritative memory
system for the Samantha persona. Some agent substrates maintain their own
native auto-memory subsystem that is injected into the session separately and
can diverge from the cerebrum (e.g. Claude Code's `~/.claude` auto-memory).

To avoid dual-memory divergence, samantha-llm disables a substrate's native
auto-memory when launching that substrate, so the cerebrum is the sole memory
in session. This is default-on and per-substrate: each substrate's disable is
mapped to the env var that substrate respects.

This module is standalone (importable by tests) and loaded by the
`samantha-llm` launcher at session start.

Public API:
    native_auto_memory_disable_env(command) -> dict
    build_child_env(agent_config, base_env=None) -> dict
"""

import os
from typing import Mapping, Optional

# Map a substrate identifier to the env vars that disable its native auto-memory.
# Add new substrates here as their disable env vars become known.
_SUBSTRATE_DISABLE_ENV = {
    "claude": {"CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"},
}


def _leading_token(command: str) -> str:
    """Return the first whitespace-delimited token of a command string, lowercased."""
    return command.strip().split()[0].lower() if command and command.strip() else ""


def native_auto_memory_disable_env(command: Optional[str]) -> dict:
    """Return env vars that disable the substrate's native auto-memory.

    Detection is based on the leading command token (e.g. `claude`, `codex`,
    `ollama`). Substrates without a known disable mechanism return an empty
    dict, which is harmless to merge.

    Args:
        command: The agent's launch command string (e.g. "claude", "codex --no-alt-screen").

    Returns:
        A dict of env vars to set, possibly empty.
    """
    token = _leading_token(command or "")
    # Also handle path-qualified invocations like /usr/local/bin/claude.
    if token:
        token = os.path.basename(token)
    return dict(_SUBSTRATE_DISABLE_ENV.get(token, {}))


def build_child_env(
    agent_config: Mapping,
    base_env: Optional[Mapping] = None,
) -> dict:
    """Build the environment dict for an agent subprocess.

    Layers, applied in order (later layers win):

    1. ``base_env`` (defaults to a copy of ``os.environ``) so the child
       inherits PATH, HOME, etc.
    2. The substrate's native-auto-memory disable env vars, unless the agent
       config opts out via ``disable_native_auto_memory: false``. This is
       default-on: the key defaults to true, so existing configs get the
       disable without a migration.
    3. The per-agent ``env`` dict (``agent_config.get("env", {})``), applied
       last so explicit per-agent values always win. This is the general
       escape hatch for any other env vars a substrate may need, and it lets
       a user override the auto-memory disable for a specific agent if
       desired.

    The base env is never mutated.

    Args:
        agent_config: The agent's config dict (must contain ``command``;
            may contain ``disable_native_auto_memory`` and ``env``).
        base_env: Environment to inherit. Defaults to a copy of ``os.environ``.

    Returns:
        A new dict suitable for passing to ``subprocess.run(env=...)``.
    """
    env = dict(base_env if base_env is not None else os.environ)

    disable_native = agent_config.get("disable_native_auto_memory", True)
    if disable_native:
        env.update(native_auto_memory_disable_env(agent_config.get("command", "")))

    per_agent_env = agent_config.get("env", {}) or {}
    env.update(per_agent_env)

    return env
