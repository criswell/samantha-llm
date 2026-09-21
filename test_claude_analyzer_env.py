#!/usr/bin/env python3
"""Tests for ClaudeAnalyzer env building (headless auth remapping).

Hermetic: no claude invocation, no real user config reads (all config
paths are explicit temp files), all env changes are restored.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from claude_analyzer import ClaudeAnalyzer


class BuildEnvTests(unittest.TestCase):
    AUTH_KEYS = ('ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN',
                 'GATEWAY_KEY_PRIMARY', 'GATEWAY_KEY_SECONDARY')

    def setUp(self):
        self._saved = {k: os.environ.get(k) for k in self.AUTH_KEYS}
        for k in self.AUTH_KEYS:
            os.environ.pop(k, None)
        self.tmp = tempfile.TemporaryDirectory()
        self.config_path = Path(self.tmp.name) / 'config.json'

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.tmp.cleanup()

    def write_config(self, payload):
        self.config_path.write_text(json.dumps(payload))

    def test_no_config_file_no_injection(self):
        env = ClaudeAnalyzer._build_env(config_path=self.config_path)
        self.assertNotIn('ANTHROPIC_AUTH_TOKEN', env)

    def test_explicit_api_key_wins(self):
        os.environ['ANTHROPIC_API_KEY'] = 'sk-explicit'
        os.environ['GATEWAY_KEY_PRIMARY'] = 'gw-key'
        self.write_config({"subconscious": {"auth_token_env_vars": ["GATEWAY_KEY_PRIMARY"]}})
        env = ClaudeAnalyzer._build_env(config_path=self.config_path)
        self.assertNotIn('ANTHROPIC_AUTH_TOKEN', env)
        self.assertEqual(env['ANTHROPIC_API_KEY'], 'sk-explicit')

    def test_explicit_auth_token_not_overridden(self):
        os.environ['ANTHROPIC_AUTH_TOKEN'] = 'tok-explicit'
        os.environ['GATEWAY_KEY_PRIMARY'] = 'gw-key'
        self.write_config({"subconscious": {"auth_token_env_vars": ["GATEWAY_KEY_PRIMARY"]}})
        env = ClaudeAnalyzer._build_env(config_path=self.config_path)
        self.assertEqual(env['ANTHROPIC_AUTH_TOKEN'], 'tok-explicit')

    def test_remap_first_configured_key_with_value(self):
        os.environ['GATEWAY_KEY_PRIMARY'] = 'gw-primary'
        self.write_config({"subconscious": {"auth_token_env_vars": ["GATEWAY_KEY_PRIMARY", "GATEWAY_KEY_SECONDARY"]}})
        env = ClaudeAnalyzer._build_env(config_path=self.config_path)
        self.assertEqual(env['ANTHROPIC_AUTH_TOKEN'], 'gw-primary')

    def test_remap_falls_through_empty_values(self):
        os.environ['GATEWAY_KEY_PRIMARY'] = ''
        os.environ['GATEWAY_KEY_SECONDARY'] = 'gw-secondary'
        self.write_config({"subconscious": {"auth_token_env_vars": ["GATEWAY_KEY_PRIMARY", "GATEWAY_KEY_SECONDARY"]}})
        env = ClaudeAnalyzer._build_env(config_path=self.config_path)
        self.assertEqual(env['ANTHROPIC_AUTH_TOKEN'], 'gw-secondary')

    def test_no_matching_env_values_no_injection(self):
        self.write_config({"subconscious": {"auth_token_env_vars": ["GATEWAY_KEY_PRIMARY"]}})
        env = ClaudeAnalyzer._build_env(config_path=self.config_path)
        self.assertNotIn('ANTHROPIC_AUTH_TOKEN', env)

    def test_malformed_config_treated_as_unconfigured(self):
        self.config_path.write_text('{not valid json')
        env = ClaudeAnalyzer._build_env(config_path=self.config_path)
        self.assertNotIn('ANTHROPIC_AUTH_TOKEN', env)

    def test_non_list_config_value_treated_as_unconfigured(self):
        os.environ['GATEWAY_KEY_PRIMARY'] = 'gw-primary'
        self.write_config({"subconscious": {"auth_token_env_vars": "GATEWAY_KEY_PRIMARY"}})
        env = ClaudeAnalyzer._build_env(config_path=self.config_path)
        self.assertNotIn('ANTHROPIC_AUTH_TOKEN', env)

    def test_non_string_entries_filtered(self):
        names = ClaudeAnalyzer._auth_token_env_names(config_path=self.config_path)
        self.assertEqual(names, [])
        self.config_path.write_text(json.dumps(
            {"subconscious": {"auth_token_env_vars": ["GOOD_KEY", 42, None, ""]}}))
        names = ClaudeAnalyzer._auth_token_env_names(config_path=self.config_path)
        self.assertEqual(names, ["GOOD_KEY"])

    def test_missing_subconscious_section_defaults_empty(self):
        self.write_config({"agents": {"claude": {"command": "claude"}}})
        names = ClaudeAnalyzer._auth_token_env_names(config_path=self.config_path)
        self.assertEqual(names, [])

    def test_parent_env_inherited(self):
        os.environ['GATEWAY_KEY_PRIMARY'] = 'gw-primary'
        self.write_config({"subconscious": {"auth_token_env_vars": ["GATEWAY_KEY_PRIMARY"]}})
        env = ClaudeAnalyzer._build_env(config_path=self.config_path)
        self.assertIn('PATH', env)
        self.assertEqual(env['GATEWAY_KEY_PRIMARY'], 'gw-primary')


if __name__ == '__main__':
    unittest.main()
