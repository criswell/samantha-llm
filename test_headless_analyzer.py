#!/usr/bin/env python3
"""
Tests for the config-driven headless agent analyzer.

Covers spec resolution (built-in, custom, unknown), delegation routing for
claude/codex names, and end-to-end analysis through a fake stdin agent.
"""

import os
import subprocess
import sys
import tempfile
import time
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

        class FakeProc:
            returncode = 0
            pid = 0

            def communicate(self, input=None, timeout=None):
                seen['input'] = input
                return ('no analysis content', '')

        def fake_popen(command, **kwargs):
            seen['command'] = command
            return FakeProc()

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
            with mock.patch.object(h.subprocess, 'Popen', side_effect=fake_popen):
                analyzer.analyze(payload_path)
            self.assertIn('SYSTEM PROMPT TEXT', seen['input'])
            self.assertIn('CONVERSATION BODY', seen['input'])
            self.assertLess(
                seen['input'].index('SYSTEM PROMPT TEXT'),
                seen['input'].index('CONVERSATION BODY'),
            )
            self.assertEqual(seen['command'], 'fake-agent')
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


class TimeoutBehaviorTests(unittest.TestCase):
    """Regression tests for the 2026-11-13/14 chunk-retry stall.

    subprocess.run's timeout killed only the direct child (the shell), leaving
    CLI-spawned helpers alive with the stdin pipe held open. An unattended
    chunk_retry then sat for hours (server hangs of 128 and 308 minutes in the
    session 20261113_172955 log) instead of failing at the 5-minute cap.
    """

    def test_timeout_kills_whole_process_tree(self):
        """A timed-out invocation must not leave the command tree running."""
        # Snapshot /proc NOW: any 'sleep 300' process started after this point
        # (by start time) is this test's tree, even if re-parented when killed.
        # A bare `pgrep -f sleep 300` is a false premise on a multitasking
        # box: it matches strays from earlier crashed runs and other trees
        # whose cmdline merely contains the string (the sh -c wrapper among
        # them) - the source of the 2026-11-16 suite flake.
        def start_ticks(pid):
            with open(f'/proc/{pid}/stat', encoding='ascii', errors='replace') as f:
                return int(f.read().rsplit(') ', 1)[1].split()[19])

        before = start_ticks(os.getpid())
        analyzer = h.HeadlessAgentAnalyzer(
            Path('/dev/null'),
            # Child daemonizes a grandchild that inherits stdin and sleeps long.
            h.HeadlessSpec(command='sleep 30 & sleep 300'),
            agent_name='fake',
            timeout=2,
        )
        with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as f:
            f.write('payload')
            path = Path(f.name)
        try:
            with mock.patch.object(h, 'DEFAULT_TIMEOUT_SECONDS', 2):
                start = time.monotonic()
                with self.assertRaises(RuntimeError) as ctx:
                    analyzer.analyze(path)
                elapsed = time.monotonic() - start
            self.assertIn('timed out', str(ctx.exception))
            # The 2s cap must actually be enforced (was: unbounded stall).
            self.assertLess(elapsed, 20)
            # Give any survivor a moment to show up, then require none among
            # processes started during this test. A SIGKILLed process that is
            # dead but not yet reaped (Z state) is not an escapee; only live
            # state counts.
            time.sleep(0.3)
            pgrep = subprocess.run(
                ['pgrep', '-f', 'sleep 300'], capture_output=True, text=True
            )
            survivors = []
            for pid in pgrep.stdout.split():
                try:
                    fields = open(f'/proc/{pid}/stat',
                                  encoding='ascii', errors='replace').read().rsplit(') ', 1)[1].split()
                    state, started = fields[2], int(fields[19])
                except (FileNotFoundError, IndexError, ValueError):
                    continue  # vanished between pgrep and stat: was dying
                if state != 'Z' and started >= before:
                    survivors.append(f'{pid}:{state}')
            self.assertEqual(
                survivors, [],
                'orphaned grandchild survived the timeout')
        finally:
            path.unlink()

    def test_timeout_error_mentions_configured_seconds(self):
        analyzer = h.HeadlessAgentAnalyzer(
            Path('/dev/null'), h.HeadlessSpec(command='sleep 300'),
            agent_name='fake', timeout=120,
        )
        with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as f:
            f.write('payload')
            path = Path(f.name)
        try:
            with self.assertRaises(RuntimeError) as ctx:
                analyzer.analyze(path)
            self.assertIn('timed out after 2 minutes', str(ctx.exception))
        finally:
            path.unlink()

    def test_fmt_timeout_shapes(self):
        self.assertEqual(h._fmt_timeout(300), '5 minutes')
        self.assertEqual(h._fmt_timeout(60), '1 minute')
        self.assertEqual(h._fmt_timeout(120), '2 minutes')
        self.assertEqual(h._fmt_timeout(45), '45 seconds')

    def test_resolve_timeout_from_config(self):
        self.assertEqual(h._resolve_timeout({'headless_timeout_seconds': 600}), 600)
        self.assertEqual(h._resolve_timeout({}), h.DEFAULT_TIMEOUT_SECONDS)
        self.assertEqual(h._resolve_timeout({'headless_timeout_seconds': 'junk'}),
                         h.DEFAULT_TIMEOUT_SECONDS)
        self.assertEqual(h._resolve_timeout({'headless_timeout_seconds': 5}), 30)  # floor

    def test_create_agent_analyzer_applies_config_timeout(self):
        with mock.patch.object(h, 'load_subconscious_config', return_value={
            'analyzer_agent': 'fake',
            'headless_commands': {'fake': {'command': 'cat'}},
            'headless_timeout_seconds': 777,
        }), mock.patch.object(h.shutil, 'which', return_value='/usr/bin/cat'):
            analyzer, name = h.create_agent_analyzer(Path('/dev/null'))
        self.assertEqual(name, 'fake')
        self.assertEqual(analyzer.timeout, 777)


if __name__ == '__main__':
    unittest.main(verbosity=2)
