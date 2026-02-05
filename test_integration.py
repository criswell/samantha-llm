#!/usr/bin/env python3
"""
Integration tests for session-isolated processing system.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from session_workspace import SessionWorkspace, get_active_sessions
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


if __name__ == '__main__':
    unittest.main(verbosity=2)
