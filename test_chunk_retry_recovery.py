#!/usr/bin/env python3
"""
Tests for the chunk_retry recovery helpers: recombine_session_analyses()
and restamp_session_complete().

These close the "recovered session stays partial forever" loop: the worker
only combines chunk outputs and stamps terminal status when ITS main loop
finishes, so a session whose last chunks were recovered by chunk_retry kept
stale _full/_parsed files and a 'partial' stamp that blocked merge.
"""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import chunk_retry
import suspend_inhibit
from session_workspace import SessionWorkspace


CHUNK_TEMPLATE = """## Part 1: Detailed Session Notes

Narrative for chunk {n}. Discusses topic {topic}.

## Part 2: High-Level Insights

### Patterns

- Pattern alpha from chunk {n}
{shared_line}

### Key Decisions

- Decision one for chunk {n}

### Action Items & TODOs (Detailed)

- [ ] TODO unique to chunk {n}

### User Preferences

- Prefers {topic}

### Key Learnings

- Learning {n}: something observed

### Session Summary

Summary text for chunk {n}.
"""


class RecoveryHelperTests(unittest.TestCase):
    """recombine + restamp on a workspace shaped like a recovered session."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cerebrum = Path(self.temp_dir) / 'cerebrum'
        self.cerebrum.mkdir()
        self.workspace = SessionWorkspace('20260205_120000', self.cerebrum)
        self.workspace.create()
        self.workspace.init_chunk_manifest(3)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def write_chunk(self, n, content=None):
        """Write one chunk analysis file in the worker's Part 1/Part 2 shape."""
        if content is None:
            content = CHUNK_TEMPLATE.format(n=n, topic=f'topic{n}',
                                            shared_line='- Pattern alpha from chunk 1')
        path = self.workspace.analyses_dir / f'analysis_20260205_120000_chunk{n}.md'
        path.write_text(content)
        return path

    def test_recombine_full_md_has_all_chunks_in_order(self):
        """_full.md must contain every chunk under its N/total header."""
        for n in (1, 2, 3):
            self.write_chunk(n)
        chunk_retry.recombine_session_analyses(self.workspace, archived=False)

        full = (self.workspace.analyses_dir /
                'analysis_20260205_120000_full.md').read_text()
        self.assertIn('# Chunk 1/3', full)
        self.assertIn('# Chunk 2/3', full)
        self.assertIn('# Chunk 3/3', full)
        # Order preserved: chunk 1's unique content before chunk 3's.
        self.assertLess(full.index('topic1'), full.index('topic3'))
        self.assertIn('---', full)  # worker's section separator

    def test_recombine_parsed_md_merges_and_dedupes(self):
        """_parsed.md merges all chunks with the worker's dedupe semantics."""
        self.write_chunk(1)
        self.write_chunk(2)
        self.write_chunk(3)
        chunk_retry.recombine_session_analyses(self.workspace, archived=False)

        parsed = (self.workspace.analyses_dir /
                  'analysis_20260205_120000_parsed.md').read_text()
        # Dedupe: 'Pattern alpha from chunk 1' appears in every chunk's Part 2
        # with identical text; case-insensitive dedupe keeps one.
        self.assertEqual(parsed.count('- Pattern alpha from chunk 1'), 1)
        # Unique per-chunk items survive.
        self.assertIn('Decision one for chunk 2', parsed)
        self.assertIn('Learning 3: something observed', parsed)
        # Summary block carries per-chunk markers.
        self.assertIn('**Chunk 1**', parsed)
        self.assertIn('**Chunk 3**', parsed)

    def test_recombine_no_chunk_files_is_a_noop(self):
        """No chunk analyses: log and return, never raise."""
        chunk_retry.recombine_session_analyses(self.workspace, archived=False)
        self.assertFalse((self.workspace.analyses_dir /
                          'analysis_20260205_120000_full.md').exists())

    def test_restamp_when_manifest_all_complete(self):
        """All chunks complete -> status re-stamped to 'complete'."""
        for n in (1, 2, 3):
            self.workspace.update_chunk_status(n, 'complete')
        self.workspace.update_status('partial', {'chunks_complete': 1})

        self.assertTrue(chunk_retry.restamp_session_complete(self.workspace))
        status = self.workspace.get_status()
        self.assertEqual(status['status'], 'complete')
        self.assertEqual(status['chunks_complete'], 3)
        self.assertEqual(status['chunks_total'], 3)
        self.assertIn('completed_at', status)

    def test_restamp_refuses_incomplete_manifest(self):
        """Manifest not all-complete: do NOT stamp complete (no lying)."""
        self.workspace.update_chunk_status(1, 'complete')
        self.workspace.update_chunk_status(2, 'failed')
        self.workspace.update_chunk_status(3, 'pending')
        self.workspace.update_status('partial')

        self.assertFalse(chunk_retry.restamp_session_complete(self.workspace))
        self.assertEqual(self.workspace.get_status()['status'], 'partial')

    def test_restamp_refuses_empty_manifest(self):
        """No manifest at all: never stamp complete."""
        self.assertFalse(chunk_retry.restamp_session_complete(self.workspace))
        self.assertEqual(self.workspace.get_status()['status'], 'processing')


class RetrySessionWiringTests(unittest.TestCase):
    """retry_session must invoke the recovery helpers on the all-complete path."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cerebrum = Path(self.temp_dir) / 'cerebrum'
        self.cerebrum.mkdir()
        self.workspace = SessionWorkspace('20260205_120000', self.cerebrum)
        self.workspace.create()
        self.workspace.init_chunk_manifest(2)
        self.prompt = (self.cerebrum / '.ai' / 'subconscious' / '.ai' /
                       'prompts' / 'analysis-prompt-v2.txt')
        self.prompt.parent.mkdir(parents=True, exist_ok=True)
        self.prompt.write_text('prompt')
        # The retry_session entry guard re-execs under systemd-inhibit; tests
        # must run unwrapped (the exec would abandon the unittest process).
        self._env_guard = os.environ.get(suspend_inhibit.INHIBIT_ENV_VAR)
        os.environ[suspend_inhibit.INHIBIT_ENV_VAR] = '1'

    def tearDown(self):
        if self._env_guard is None:
            del os.environ[suspend_inhibit.INHIBIT_ENV_VAR]
        else:
            os.environ[suspend_inhibit.INHIBIT_ENV_VAR] = self._env_guard
        shutil.rmtree(self.temp_dir)

    def test_all_complete_path_runs_recombine_and_restamp(self):
        """Recovering the last failed chunk recombines + re-stamps."""
        self.workspace.update_chunk_status(1, 'complete')
        self.workspace.update_chunk_status(2, 'failed')
        (self.workspace.analyses_dir /
         'analysis_20260205_120000_chunk1.md').write_text(
            CHUNK_TEMPLATE.format(n=1, topic='t1', shared_line=''))
        (self.workspace.analyses_dir /
         'analysis_20260205_120000_chunk2.md').write_text(
            CHUNK_TEMPLATE.format(n=2, topic='t2', shared_line=''))

        calls = []

        def fake_retry_chunk(ws, chunk_num, chunk_data, prompt_path, agent):
            calls.append(chunk_num)
            ws.update_chunk_status(chunk_num, 'complete')
            (ws.analyses_dir /
             f'analysis_{ws.session_id}_chunk{chunk_num}.md').write_text(
                CHUNK_TEMPLATE.format(n=chunk_num, topic=f't{chunk_num}',
                                      shared_line=''))
            return True

        orig = chunk_retry.retry_chunk
        chunk_retry.retry_chunk = fake_retry_chunk
        try:
            chunk_retry.retry_session('20260205_120000', self.cerebrum)
        finally:
            chunk_retry.retry_chunk = orig

        self.assertEqual(calls, [2])  # only the failed chunk was retried
        status = self.workspace.get_status()
        self.assertEqual(status['status'], 'complete')
        self.assertTrue((self.workspace.analyses_dir /
                         'analysis_20260205_120000_full.md').exists())
        parsed = (self.workspace.analyses_dir /
                  'analysis_20260205_120000_parsed.md').read_text()
        self.assertIn('Prefers t2', parsed)
        self.assertIn('**Chunk 2**', parsed)

    def test_still_failed_path_does_not_restamp(self):
        """Chunks still failing after retries: status must stay 'partial'."""
        self.workspace.update_chunk_status(1, 'failed')
        self.workspace.update_chunk_status(2, 'complete')
        (self.workspace.analyses_dir /
         'analysis_20260205_120000_chunk2.md').write_text(
            CHUNK_TEMPLATE.format(n=2, topic='t2', shared_line=''))

        def always_fails(ws, chunk_num, chunk_data, prompt_path, agent):
            ws.update_chunk_status(chunk_num, 'failed', {'attempts': 2})
            return False

        orig = chunk_retry.retry_chunk
        chunk_retry.retry_chunk = always_fails
        try:
            chunk_retry.retry_session('20260205_120000', self.cerebrum)
        finally:
            chunk_retry.retry_chunk = orig

        # retry_session itself doesn't stamp 'partial' (the worker did that
        # when its loop died); the contract here is only that it does NOT
        # stamp 'complete' and does not recombine on a non-terminal manifest.
        self.assertEqual(self.workspace.get_status()['status'], 'processing')
        self.assertFalse((self.workspace.analyses_dir /
                          'analysis_20260205_120000_full.md').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
