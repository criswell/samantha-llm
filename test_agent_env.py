#!/usr/bin/env python3
"""
Tests for agent_env: substrate-native auto-memory disable + child env building.

Samantha-llm treats the cerebrum as the authoritative memory system. When it
launches a substrate that has its own native auto-memory (e.g. Claude Code's
~/.claude auto-memory), it disables that feature so the cerebrum is the sole
memory in session, avoiding dual-memory divergence.
"""

import os
import unittest

from agent_env import build_child_env, native_auto_memory_disable_env


class TestNativeAutoMemoryDisableEnv(unittest.TestCase):
    def test_claude_command_returns_disable_var(self):
        self.assertEqual(
            native_auto_memory_disable_env("claude"),
            {"CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"},
        )

    def test_claude_command_with_flags_still_detected(self):
        # The command may include arguments; detection is on the leading token.
        self.assertEqual(
            native_auto_memory_disable_env("claude --some-flag value"),
            {"CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"},
        )

    def test_non_claude_substrate_returns_empty(self):
        for command in (
            "codex --no-alt-screen",
            "ollama launch qwen --model qwen3-coder:480b-cloud -- --bare",
            "npx copilot -i",
            "npx abacusai",
            "myagent",
        ):
            with self.subTest(command=command):
                self.assertEqual(native_auto_memory_disable_env(command), {})

    def test_empty_or_none_command_returns_empty(self):
        self.assertEqual(native_auto_memory_disable_env(""), {})
        self.assertEqual(native_auto_memory_disable_env(None), {})

    def test_command_with_leading_whitespace_detected(self):
        self.assertEqual(
            native_auto_memory_disable_env("  claude"),
            {"CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"},
        )


class TestBuildChildEnv(unittest.TestCase):
    def test_claude_agent_gets_auto_memory_disable(self):
        env = build_child_env({"command": "claude"}, base_env={})
        self.assertEqual(env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"], "1")

    def test_non_claude_agent_does_not_get_disable_var(self):
        env = build_child_env({"command": "codex --no-alt-screen"}, base_env={})
        self.assertNotIn("CLAUDE_CODE_DISABLE_AUTO_MEMORY", env)

    def test_inherits_base_env(self):
        env = build_child_env(
            {"command": "claude"}, base_env={"PATH": "/usr/bin", "HOME": "/x"}
        )
        self.assertEqual(env["PATH"], "/usr/bin")
        self.assertEqual(env["HOME"], "/x")
        self.assertEqual(env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"], "1")

    def test_opt_out_via_disable_native_auto_memory_false(self):
        env = build_child_env(
            {"command": "claude", "disable_native_auto_memory": False},
            base_env={},
        )
        self.assertNotIn("CLAUDE_CODE_DISABLE_AUTO_MEMORY", env)

    def test_opt_out_defaults_to_disabled(self):
        # Key absent -> default is to disable (default-on in code).
        env = build_child_env({"command": "claude"}, base_env={})
        self.assertIn("CLAUDE_CODE_DISABLE_AUTO_MEMORY", env)

    def test_per_agent_env_dict_is_merged(self):
        env = build_child_env(
            {"command": "claude", "env": {"MY_VAR": "hello"}},
            base_env={},
        )
        self.assertEqual(env["MY_VAR"], "hello")
        self.assertEqual(env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"], "1")

    def test_per_agent_env_overrides_disable(self):
        # The per-agent env layer is applied last and wins, so a user can
        # explicitly re-enable auto-memory by overriding the var.
        env = build_child_env(
            {"command": "claude", "env": {"CLAUDE_CODE_DISABLE_AUTO_MEMORY": "0"}},
            base_env={},
        )
        self.assertEqual(env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"], "0")

    def test_per_agent_env_does_not_leak_into_non_claude(self):
        env = build_child_env(
            {"command": "codex", "env": {"CODEX_VAR": "x"}}, base_env={}
        )
        self.assertEqual(env["CODEX_VAR"], "x")
        self.assertNotIn("CLAUDE_CODE_DISABLE_AUTO_MEMORY", env)

    def test_base_env_is_not_mutated(self):
        base = {"PATH": "/usr/bin"}
        build_child_env({"command": "claude"}, base_env=base)
        self.assertEqual(base, {"PATH": "/usr/bin"})

    def test_defaults_to_os_environ_when_base_env_omitted(self):
        # base_env defaults to a copy of os.environ so the child inherits PATH etc.
        env = build_child_env({"command": "claude"})
        # Should at least contain whatever PATH the process has, plus the disable.
        self.assertIn("CLAUDE_CODE_DISABLE_AUTO_MEMORY", env)


if __name__ == "__main__":
    unittest.main()
