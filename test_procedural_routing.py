#!/usr/bin/env python3
"""
Tests for procedural_extractor's LLM routing.

Regression coverage for the 2026-11-12 finding: _call_llm used its own
ANTHROPIC_API_KEY -> claude CLI ladder, which 403s on boxes where the
config-driven headless analyzer (subconscious.analyzer_agent) is the only
working route. Routing now tries the config-driven agent first and only
falls back to the legacy ladder when no explicit analyzer is configured.

E2E (fake headless agent through the real worker main()) lives in the
session record; these tests cover the routing logic in isolation.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))

import procedural_extractor as pe


class ConfigDrivenRoutingTests(unittest.TestCase):
    """_call_llm routes through the config-driven headless agent first."""

    def setUp(self):
        """Pin SAMANTHA_LLM_CONFIG so user config never leaks into tests."""
        self.tmp = tempfile.TemporaryDirectory()
        self.config_path = Path(self.tmp.name) / 'config.json'
        os.environ['SAMANTHA_LLM_CONFIG'] = str(self.config_path)
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(os.environ.pop, 'SAMANTHA_LLM_CONFIG', None)

    def _write_config(self, sub_config):
        import json
        self.config_path.write_text(json.dumps({'subconscious': sub_config}))

    def test_config_driven_agent_used(self):
        """An explicit analyzer_agent routes through run_raw, not the legacy ladder."""
        self._write_config({
            'analyzer_agent': 'fake',
            'headless_commands': {'fake': {'command': 'fake-agent'}},
        })
        # fake-agent must exist in PATH for create_agent_analyzer's which() check
        fake_bin = Path(self.tmp.name) / 'bin'
        fake_bin.mkdir(exist_ok=True)
        fake_cmd = fake_bin / 'fake-agent'
        fake_cmd.write_text('#!/bin/sh\n')
        fake_cmd.chmod(0o755)
        os.environ['PATH'] = str(fake_bin) + os.pathsep + os.environ.get('PATH', '')
        with mock.patch('headless_agent_analyzer.HeadlessAgentAnalyzer.run_raw',
                        return_value='{"observations": []}') as raw, \
             mock.patch('procedural_extractor._call_anthropic') as api, \
             mock.patch('procedural_extractor._call_claude_cli') as cli:
            result = pe._call_llm(Path('/fake/prompt.txt'), 'ANALYSIS', lambda m: None)
        raw.assert_called_once()
        api.assert_not_called()
        cli.assert_not_called()
        self.assertEqual(result, '{"observations": []}')

    def test_procedural_prompt_passed_to_analyzer(self):
        """The analyzer is constructed with the PROCEDURAL prompt path."""
        self._write_config({
            'analyzer_agent': 'fake',
            'headless_commands': {'fake': {'command': 'fake-agent'}},
        })
        fake_bin = Path(self.tmp.name) / 'bin'
        fake_bin.mkdir(exist_ok=True)
        fake_cmd = fake_bin / 'fake-agent'
        fake_cmd.write_text('#!/bin/sh\n')
        fake_cmd.chmod(0o755)
        os.environ['PATH'] = str(fake_bin) + os.pathsep + os.environ.get('PATH', '')
        prompt_path = Path('/fake/procedural-prompt.txt')
        seen = {}
        with mock.patch('headless_agent_analyzer.HeadlessAgentAnalyzer.run_raw',
                        return_value='{}'):
            import headless_agent_analyzer
            orig_init = headless_agent_analyzer.HeadlessAgentAnalyzer.__init__

            def spy_init(self, prompt_path, *a, **k):
                seen['prompt'] = prompt_path
                orig_init(self, prompt_path, *a, **k)

            with mock.patch.object(headless_agent_analyzer.HeadlessAgentAnalyzer,
                                   '__init__', spy_init):
                pe._call_llm(prompt_path, 'ANALYSIS', lambda m: None)
        self.assertEqual(seen['prompt'], prompt_path)

    def test_no_config_falls_back_to_legacy_ladder(self):
        """No analyzer_agent config: legacy ladder still works (anthropic key)."""
        self._write_config({})
        os.environ['ANTHROPIC_API_KEY'] = 'fake-key'
        self.addCleanup(os.environ.pop, 'ANTHROPIC_API_KEY', None)
        with mock.patch('procedural_extractor._call_anthropic',
                        return_value='{}') as api, \
             mock.patch('procedural_extractor._call_claude_cli') as cli:
            result = pe._call_llm(Path('/fake/prompt.txt'), 'ANALYSIS', lambda m: None)
        api.assert_called_once()
        cli.assert_not_called()
        self.assertEqual(result, '{}')

    def test_auto_config_falls_back_to_legacy_ladder(self):
        """analyzer_agent='auto' means no explicit request: legacy ladder."""
        self._write_config({'analyzer_agent': 'auto'})
        os.environ['ANTHROPIC_API_KEY'] = 'fake-key'
        self.addCleanup(os.environ.pop, 'ANTHROPIC_API_KEY', None)
        with mock.patch('procedural_extractor._call_anthropic',
                        return_value='{}') as api:
            result = pe._call_llm(Path('/fake/prompt.txt'), 'ANALYSIS', lambda m: None)
        api.assert_called_once()
        self.assertEqual(result, '{}')

    def test_explicit_config_failure_raises(self):
        """An explicit analyzer_agent that fails must raise, not silently 403 on claude.

        Mirrors the analyzer_factory step-1.5 semantics: explicit config
        requests surface failures instead of falling through to the legacy
        ladder (which 403s on the abacus-keystore box).
        """
        self._write_config({
            'analyzer_agent': 'fake',
            'headless_commands': {'fake': {'command': 'fake-agent'}},
        })
        fake_bin = Path(self.tmp.name) / 'bin'
        fake_bin.mkdir(exist_ok=True)
        fake_cmd = fake_bin / 'fake-agent'
        fake_cmd.write_text('#!/bin/sh\n')
        fake_cmd.chmod(0o755)
        os.environ['PATH'] = str(fake_bin) + os.pathsep + os.environ.get('PATH', '')
        with mock.patch('headless_agent_analyzer.HeadlessAgentAnalyzer.run_raw',
                        side_effect=RuntimeError('agent exploded')):
            with self.assertRaises(RuntimeError):
                pe._call_llm(Path('/fake/prompt.txt'), 'ANALYSIS', lambda m: None)

    def test_unresolvable_agent_falls_back_when_not_explicit(self):
        """An unresolvable agent name without explicit config -> legacy ladder."""
        # analyzer_agent absent but agents configured elsewhere: resolution
        # returns None -> create_agent_analyzer returns (None, None)
        self._write_config({'headless_commands': {}})
        os.environ['ANTHROPIC_API_KEY'] = 'fake-key'
        self.addCleanup(os.environ.pop, 'ANTHROPIC_API_KEY', None)
        with mock.patch('procedural_extractor._call_anthropic',
                        return_value='{}') as api:
            result = pe._call_llm(Path('/fake/prompt.txt'), 'ANALYSIS', lambda m: None)
        api.assert_called_once()
        self.assertEqual(result, '{}')


if __name__ == '__main__':
    unittest.main(verbosity=2)
