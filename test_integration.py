#!/usr/bin/env python3
"""
Integration tests for session-isolated processing system.
"""

import unittest
import json
import tempfile
import shutil
from pathlib import Path
from session_workspace import SessionWorkspace, get_active_sessions, get_failed_sessions
from bootstrap_status import display_processing_status, get_status_summary
from merge_sessions import merge_completed_sessions


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system."""

    def setUp(self):
        """Create a temporary cerebrum directory for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.cerebrum_path = Path(self.temp_dir) / 'cerebrum'
        self.cerebrum_path.mkdir()

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    def test_end_to_end_workflow(self):
        """Test complete workflow: create session, process, merge."""
        # Step 1: Create session workspace
        session1 = SessionWorkspace('20260205_120000', self.cerebrum_path)
        session1.create()

        # Simulate chunk processing
        session1.init_chunk_manifest(3)
        session1.update_chunk_status(1, 'complete', {'patterns_count': 5})
        session1.update_chunk_status(2, 'complete', {'patterns_count': 3})
        session1.update_chunk_status(3, 'complete', {'patterns_count': 4})

        # Create mock guidance
        guidance_content = """---
last_updated: 2026-02-05T12:00:00
---

# Subconscious Guidance

## Recent Sessions

- **2026-02-05** (15min, /test/workspace): Test session [[analysis_20260205_120000_full.md]]
"""
        session1.guidance_file.write_text(guidance_content)

        # Create mock memory
        memory_content = """---
date: 2026-02-05
topics: [test]
importance: high
type: technical
---

# Test Memory

This is a test memory from the session.
"""
        memory_file = session1.memories_dir / '2026-02-05_test_memory.md'
        memory_file.write_text(memory_content)

        # Mark session complete
        session1.mark_complete()

        # Step 2: Check status
        active = get_active_sessions(self.cerebrum_path)
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0][1]['status'], 'complete')

        status_summary = get_status_summary(self.cerebrum_path)
        self.assertTrue(status_summary['active'])
        self.assertEqual(status_summary['complete'], 1)

        # Step 3: Merge sessions
        merge_completed_sessions(self.cerebrum_path, dry_run=False)

        # Check that session was archived
        archive_dir = self.cerebrum_path / '.ai' / 'subconscious' / '.ai' / 'processed' / '20260205_120000'
        self.assertTrue(archive_dir.exists())

        # Check that memory was moved
        memory_dest = self.cerebrum_path / '.ai' / 'short-term-memory' / '.ai' / '2026-02-05_test_memory.md'
        self.assertTrue(memory_dest.exists())

        # Check that guidance was merged
        main_guidance = self.cerebrum_path / '.ai' / 'subconscious' / '.ai' / 'guidance.md'
        self.assertTrue(main_guidance.exists())

        # Step 4: Verify no active sessions after merge
        active_after = get_active_sessions(self.cerebrum_path)
        self.assertEqual(len(active_after), 0)

    def test_multiple_sessions(self):
        """Test handling multiple concurrent sessions."""
        # Create 3 sessions
        session1 = SessionWorkspace('20260205_120000', self.cerebrum_path)
        session1.create()
        session1.init_chunk_manifest(2)
        session1.update_chunk_status(1, 'complete')
        session1.update_chunk_status(2, 'failed', {'error': 'timeout'})

        session2 = SessionWorkspace('20260205_130000', self.cerebrum_path)
        session2.create()
        session2.init_chunk_manifest(1)
        session2.update_chunk_status(1, 'complete')
        session2.mark_complete()

        session3 = SessionWorkspace('20260205_140000', self.cerebrum_path)
        session3.create()
        session3.mark_failed('Test error')

        # Check active sessions
        active = get_active_sessions(self.cerebrum_path)
        self.assertEqual(len(active), 2)  # processing and complete, not failed

        # Get status summary
        status = get_status_summary(self.cerebrum_path)
        self.assertEqual(status['processing'], 1)
        self.assertEqual(status['complete'], 1)

    def test_failed_chunk_tracking(self):
        """Test tracking of failed chunks for retry."""
        session = SessionWorkspace('20260205_120000', self.cerebrum_path)
        session.create()

        # Initialize chunks
        session.init_chunk_manifest(5)

        # Mark some as complete, some as failed
        session.update_chunk_status(1, 'complete')
        session.update_chunk_status(2, 'failed', {'error': 'timeout', 'attempts': 1})
        session.update_chunk_status(3, 'complete')
        session.update_chunk_status(4, 'failed', {'error': 'timeout', 'attempts': 2})
        session.update_chunk_status(5, 'processing')

        # Check manifest
        manifest = session.get_chunk_manifest()
        self.assertEqual(manifest['chunks']['1']['status'], 'complete')
        self.assertEqual(manifest['chunks']['2']['status'], 'failed')
        self.assertEqual(manifest['chunks']['2']['attempts'], 1)
        self.assertEqual(manifest['chunks']['4']['attempts'], 2)

    def test_chunk_failure_counts(self):
        """chunk_failure_counts() tallies complete/failed/total from the manifest."""
        session = SessionWorkspace('20260205_120000', self.cerebrum_path)
        session.create()
        session.init_chunk_manifest(4)
        session.update_chunk_status(1, 'complete')
        session.update_chunk_status(2, 'failed')
        session.update_chunk_status(3, 'complete')
        # chunk 4 stays pending

        counts = session.chunk_failure_counts()
        self.assertEqual(counts['complete'], 2)
        self.assertEqual(counts['failed'], 1)
        self.assertEqual(counts['total'], 4)

    def test_chunk_failure_counts_no_manifest(self):
        """No manifest (non-LLM path) means zero totals, not a crash."""
        session = SessionWorkspace('20260205_120000', self.cerebrum_path)
        session.create()

        counts = session.chunk_failure_counts()
        self.assertEqual(counts, {'complete': 0, 'failed': 0, 'total': 0})

    def test_workspace_base_dir_override(self):
        """SessionWorkspace can point at the processed/ archive (chunk_retry path)."""
        # Create a session in the normal place, then archive it the way
        # merge_sessions.archive_session does (move to processed/<id>).
        session = SessionWorkspace('20260205_120000', self.cerebrum_path)
        session.create()
        session.init_chunk_manifest(2)
        session.update_chunk_status(1, 'complete')
        session.update_chunk_status(2, 'failed')

        processed_base = self.cerebrum_path / '.ai' / 'subconscious' / '.ai' / 'processed'
        processed_base.mkdir(parents=True)
        shutil.move(str(session.root), str(processed_base / '20260205_120000'))

        # The override constructor must find the archived workspace with its
        # manifest intact.
        archived_ws = SessionWorkspace('20260205_120000', self.cerebrum_path,
                                       base_dir=processed_base)
        self.assertTrue(archived_ws.root.exists())
        counts = archived_ws.chunk_failure_counts()
        self.assertEqual(counts['complete'], 1)
        self.assertEqual(counts['failed'], 1)

    def test_get_failed_sessions(self):
        """get_failed_sessions surfaces failed (not partial) workspaces; partial stays active."""
        failed = SessionWorkspace('20260205_120000', self.cerebrum_path)
        failed.create()
        failed.mark_failed('boom')

        partial = SessionWorkspace('20260205_130000', self.cerebrum_path)
        partial.create()
        partial.update_status('partial', {'chunks_complete': 3, 'chunks_failed': 2})

        healthy = SessionWorkspace('20260205_140000', self.cerebrum_path)
        healthy.create()
        healthy.mark_complete()

        failed_sessions = get_failed_sessions(self.cerebrum_path)
        ids = sorted(ws.session_id for ws, _ in failed_sessions)
        self.assertEqual(ids, ['20260205_120000'])

        # Partial is retrievable via get_active_sessions (it holds recoverable memories)
        active = get_active_sessions(self.cerebrum_path)
        active_ids = sorted(ws.session_id for ws, _ in active)
        self.assertEqual(active_ids, ['20260205_130000', '20260205_140000'])


class TestBootstrapStatusFailureSurfacing(unittest.TestCase):
    """bootstrap_status must surface failed/partial sessions loudly (item 8.1)."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cerebrum_path = Path(self.temp_dir) / 'cerebrum'
        self.cerebrum_path.mkdir()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_summary_flags_failed_sessions(self):
        """get_status_summary reports needs_attention for failed sessions."""
        from bootstrap_status import get_status_summary

        failed = SessionWorkspace('20260205_120000', self.cerebrum_path)
        failed.create()
        failed.mark_failed('all chunks died')

        summary = get_status_summary(self.cerebrum_path)
        self.assertTrue(summary['active'])
        self.assertEqual(summary['failed'], 1)
        self.assertTrue(summary['needs_attention'])

    def test_display_shows_failed_section(self):
        """display_processing_status prints the FAILED banner for failed sessions."""
        import io
        import contextlib
        from bootstrap_status import display_processing_status

        failed = SessionWorkspace('20260205_120000', self.cerebrum_path)
        failed.create()
        failed.mark_failed('all 20 chunks failed')

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            result = display_processing_status(self.cerebrum_path)

        output = buf.getvalue()
        self.assertTrue(result)
        self.assertIn('FAILED', output)
        self.assertIn('chunk_retry.py', output)
        # Must NOT show the green awaiting-merge banner for a failed session
        self.assertNotIn('Awaiting Merge', output)

    def test_display_shows_partial_section(self):
        """display_processing_status prints the PARTIAL banner with retry hint."""
        import io
        import contextlib
        from bootstrap_status import display_processing_status

        partial = SessionWorkspace('20260205_120000', self.cerebrum_path)
        partial.create()
        partial.update_status('partial', {
            'chunks_complete': 3, 'chunks_failed': 2, 'chunks_total': 5
        })

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            result = display_processing_status(self.cerebrum_path)

        output = buf.getvalue()
        self.assertTrue(result)
        self.assertIn('PARTIAL', output)
        self.assertIn('3/5 complete', output)

    def test_no_sessions_returns_false(self):
        """No sessions of any status: display returns False (healthy)."""
        from bootstrap_status import display_processing_status
        self.assertFalse(display_processing_status(self.cerebrum_path))


class TestFinalizeIndexDedup(unittest.TestCase):
    """finalize_session_memories dedups index entries by filename (item 8.4)."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cerebrum_path = Path(self.temp_dir) / 'cerebrum'
        self.cerebrum_path.mkdir()
        self.workspace = SessionWorkspace('20260205_120000', self.cerebrum_path)
        self.workspace.create()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def _write_memory(self, name, importance='high', body='v1'):
        memory_file = self.workspace.memories_dir / name
        memory_file.write_text(f"""---
date: 2026-02-05
topics: [test]
importance: {importance}
type: session-analysis
---

# Test Memory

{body}
""")
        return memory_file

    def _finalize(self):
        from subconscious_worker import finalize_session_memories
        logs = []
        finalize_session_memories(self.workspace, self.cerebrum_path, logs.append)
        return logs

    def _index(self):
        index_file = self.cerebrum_path / '.ai' / 'short-term-memory' / '.ai' / 'index.json'
        with open(index_file) as f:
            return json.load(f)

    def test_finalize_updates_existing_entry_instead_of_duplicating(self):
        """Re-finalizing the same memory file keeps ONE index entry."""
        self._write_memory('2026-02-05_session_analysis.md')
        self._finalize()
        self._finalize()  # retry/re-finalize path

        index = self._index()
        high = index['recent']['high_importance']
        matches = [e for e in high if e['file'] == '2026-02-05_session_analysis.md']
        self.assertEqual(len(matches), 1)

    def test_finalize_overwrites_memory_file_in_place(self):
        """Re-finalize rewrites the memory file; no suffixed collision copy."""
        self._write_memory('2026-02-05_session_analysis.md', body='v1')
        self._finalize()
        self._write_memory('2026-02-05_session_analysis.md', body='v2 updated')
        self._finalize()

        mem_dir = self.cerebrum_path / '.ai' / 'short-term-memory' / '.ai'
        files = sorted(p.name for p in mem_dir.glob('2026-02-05_session_analysis*'))
        self.assertEqual(files, ['2026-02-05_session_analysis.md'])
        self.assertIn('v2 updated', (mem_dir / files[0]).read_text())

    def test_finalize_total_memories_not_inflated(self):
        """total_memories reflects distinct entries, not finalize passes."""
        self._write_memory('2026-02-05_session_analysis.md')
        self._finalize()
        self._finalize()
        self._finalize()

        index = self._index()
        self.assertEqual(index['total_memories'], 1)

    def test_finalize_distinct_memories_both_counted(self):
        """Two different memory files = two entries (dedup is per-file, not global)."""
        self._write_memory('2026-02-05_session_analysis.md')
        self._write_memory('2026-02-05_other_memory.md', importance='medium')
        self._finalize()

        index = self._index()
        self.assertEqual(index['total_memories'], 2)
        self.assertEqual(len(index['recent']['high_importance']), 1)
        self.assertEqual(len(index['recent']['medium_importance']), 1)

    def test_finalize_importance_promotion_moves_entry(self):
        """An updated memory with raised importance moves between buckets."""
        self._write_memory('2026-02-05_session_analysis.md', importance='medium')
        self._finalize()
        self._write_memory('2026-02-05_session_analysis.md', importance='high')
        self._finalize()

        index = self._index()
        high_files = [e['file'] for e in index['recent']['high_importance']]
        med_files = [e['file'] for e in index['recent']['medium_importance']]
        self.assertIn('2026-02-05_session_analysis.md', high_files)
        self.assertNotIn('2026-02-05_session_analysis.md', med_files)


class TestMoveMemoriesConflictPolicy(unittest.TestCase):
    """merge_sessions.move_memories: identical content skips, distinct content suffixes (item 8.4)."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cerebrum_path = Path(self.temp_dir) / 'cerebrum'
        self.cerebrum_path.mkdir()
        self.workspace = SessionWorkspace('20260205_120000', self.cerebrum_path)
        self.workspace.create()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def _write(self, dest, content):
        dest.write_text(content)

    def test_identical_content_not_duplicated(self):
        """Byte-identical memory on disk = skip, no suffixed copy."""
        from merge_sessions import move_memories

        mem_dir = self.cerebrum_path / '.ai' / 'short-term-memory' / '.ai'
        mem_dir.mkdir(parents=True)
        self._write(mem_dir / '2026-02-05_mem.md', '# Same')
        self._write(self.workspace.memories_dir / '2026-02-05_mem.md', '# Same')

        moved = move_memories(self.cerebrum_path, self.workspace)
        self.assertEqual(moved, 0)
        files = sorted(p.name for p in mem_dir.glob('2026-02-05_mem*'))
        self.assertEqual(files, ['2026-02-05_mem.md'])

    def test_different_content_keeps_both(self):
        """Different content = suffixed session-id copy; nothing destroyed."""
        from merge_sessions import move_memories

        mem_dir = self.cerebrum_path / '.ai' / 'short-term-memory' / '.ai'
        mem_dir.mkdir(parents=True)
        self._write(mem_dir / '2026-02-05_mem.md', '# Version A')
        self._write(self.workspace.memories_dir / '2026-02-05_mem.md', '# Version B')

        moved = move_memories(self.cerebrum_path, self.workspace)
        self.assertEqual(moved, 1)
        files = sorted(p.name for p in mem_dir.glob('2026-02-05_mem*'))
        self.assertEqual(files, ['2026-02-05_mem.md', '2026-02-05_mem_20260205_120000.md'])
        self.assertIn('Version A', (mem_dir / '2026-02-05_mem.md').read_text())


if __name__ == '__main__':
    unittest.main(verbosity=2)
