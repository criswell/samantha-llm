#!/usr/bin/env python3
"""
Tests for the config-driven headless agent analyzer.

Covers spec resolution (built-in, custom, unknown), delegation routing for
claude/codex names, and end-to-end analysis through a fake stdin agent.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))

import headless_agent_analyzer as h


class SpecResolutionTests(unittest.TestCase):
    def test_builtin_opencode_spec(self):
        spec = h.resolve_spec('opencode', {})
        self.assertIsNotNone(spec)
        self.assertTrue(spec.command.startswith('opencode'))
        self.assertEqual(spec.input, 'stdin')

    def test_custom_spec_from_config(self):
        sub = {'headless_commands': {'foo': {'command': 'myagent --headless'}}}
        spec = h.resolve_spec('foo', sub)
        self.assertEqual(spec.command, 'myagent --headless')

    def test_custom_spec_overrides_builtin(self):
        sub = {'headless_commands': {'opencode': {'command': '/custom/opencode run'}}}
        spec = h.resolve_spec('opencode', sub)
        self.assertEqual(spec.command, '/custom/opencode run')

    def test_unknown_agent_is_none(self):
        self.assertIsNone(h.resolve_spec('no-such-agent', {}))

    def test_agent_supported_delegates(self):
        self.assertTrue(h.agent_supported('claude', {}))
        self.assertTrue(h.agent_supported('codex', {}))
        self.assertTrue(h.agent_supported('opencode', {}))
        self.assertFalse(h.agent_supported('no-such-agent', {}))

    def test_load_config_missing_file(self):
        self.assertEqual(
            h.load_subconscious_config(Path('/nonexistent/config.json')), {}
        )


class FakeAgentAnalysisTests(unittest.TestCase):
    def test_echo_agent_returns_empty_result(self):
        """A command that echoes the payload parses to an empty result."""
        analyzer = h.HeadlessAgentAnalyzer(
            Path('/dev/null'), h.HeadlessSpec(command='cat'), agent_name='fake'
        )
        with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as f:
            f.write('hello world')
            path = Path(f.name)
        try:
            result = analyzer.analyze(path)
            self.assertTrue(result.is_empty())
        finally:
            path.unlink()

    def test_failing_command_raises_runtime_error(self):
        analyzer = h.HeadlessAgentAnalyzer(
            Path('/dev/null'), h.HeadlessSpec(command='exit 3'), agent_name='fake'
        )
        with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as f:
            f.write('payload')
            path = Path(f.name)
        try:
            with self.assertRaises(RuntimeError):
                analyzer.analyze(path)
        finally:
            path.unlink()

    def test_prompt_is_prepended(self):
        """The analysis prompt must reach the agent above the payload."""
        seen = {}

        def fake_run(command, **kwargs):
            seen['input'] = kwargs.get('input', '')
            result = unittest.mock.Mock()
            result.stdout = 'no analysis content'
            result.returncode = 0
            return result

        with tempfile.NamedTemporaryFile('w', delete=False) as pf:
            pf.write('SYSTEM PROMPT TEXT')
            prompt_path = Path(pf.name)
        with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as f:
            f.write('CONVERSATION BODY')
            payload_path = Path(f.name)
        try:
            analyzer = h.HeadlessAgentAnalyzer(
                prompt_path, h.HeadlessSpec(command='fake-agent'), agent_name='fake'
            )
            with mock.patch.object(h.subprocess, 'run', side_effect=fake_run):
                analyzer.analyze(payload_path)
            self.assertIn('SYSTEM PROMPT TEXT', seen['input'])
            self.assertIn('CONVERSATION BODY', seen['input'])
            self.assertLess(
                seen['input'].index('SYSTEM PROMPT TEXT'),
                seen['input'].index('CONVERSATION BODY'),
            )
        finally:
            prompt_path.unlink()
            payload_path.unlink()


class RawOutputPersistenceTests(unittest.TestCase):
    """Regression tests for the 2026-11-12 empty-_full incident.

    HeadlessAgentAnalyzer used to discard result.stdout: the worker's
    combine step then found no analysis_<sid>_chunkN.md files, wrote
    analysis_<sid>_full.md as 0 bytes, and procedural extraction (which
    refuses empty files) never fired for any headless-agent session.
    """

    def test_raw_output_saved_with_chunk_name(self):
        """analyze() must persist stdout as analysis_<stem-minus-parsed_>.md."""
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / 'analyses'
            payload_path = Path(tmp) / 'parsed_20261112_182418_chunk7.txt'
            payload_path.write_text('CONVERSATION CHUNK')
            analyzer = h.HeadlessAgentAnalyzer(
                Path('/dev/null'), h.HeadlessSpec(command='cat'), agent_name='fake',
                output_dir=out_dir,
            )
            analyzer.analyze(payload_path)
            expected = out_dir / 'analysis_20261112_182418_chunk7.md'
            self.assertTrue(expected.exists(), f"missing raw output: {expected}")
            # 'cat' echoes prompt+payload; the file must contain the payload verbatim
            self.assertIn('CONVERSATION CHUNK', expected.read_text())

    def test_raw_output_saved_single_pass_name(self):
        """Single-pass sessions (no _chunkN suffix) get analysis_<sid>.md."""
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / 'analyses'
            payload_path = Path(tmp) / 'parsed_20261112_190000.txt'
            payload_path.write_text('WHOLE CONVERSATION')
            analyzer = h.HeadlessAgentAnalyzer(
                Path('/dev/null'), h.HeadlessSpec(command='cat'), agent_name='fake',
                output_dir=out_dir,
            )
            analyzer.analyze(payload_path)
            expected = out_dir / 'analysis_20261112_190000.md'
            self.assertTrue(expected.exists(), f"missing raw output: {expected}")
            self.assertIn('WHOLE CONVERSATION', expected.read_text())

    def test_output_dir_created_on_init(self):
        """The output dir is created at construction, like the other analyzers."""
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / 'does' / 'not' / 'exist' / 'yet'
            analyzer = h.HeadlessAgentAnalyzer(
                Path('/dev/null'), h.HeadlessSpec(command='cat'), agent_name='fake',
                output_dir=out_dir,
            )
            self.assertTrue(out_dir.exists())

    def test_no_output_dir_writes_nothing(self):
        """output_dir=None (direct CLI use) keeps the old no-persistence behavior."""
        with tempfile.TemporaryDirectory() as tmp:
            payload_path = Path(tmp) / 'parsed_x.txt'
            payload_path.write_text('payload')
            analyzer = h.HeadlessAgentAnalyzer(
                Path('/dev/null'), h.HeadlessSpec(command='cat'), agent_name='fake',
            )
            analyzer.analyze(payload_path)  # must not raise
            # nothing was written anywhere: no analysis_ file next to the payload
            self.assertEqual(list(Path(tmp).glob('analysis_*')), [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
