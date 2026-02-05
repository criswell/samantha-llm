#!/usr/bin/env python3
"""
Unit tests for session workspace management.
"""

import unittest
import json
import tempfile
import shutil
from pathlib import Path
from session_workspace import SessionWorkspace, get_session_workspaces, get_active_sessions


class TestSessionWorkspace(unittest.TestCase):
    """Test cases for SessionWorkspace class."""

    def setUp(self):
        """Create a temporary cerebrum directory for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.cerebrum_path = Path(self.temp_dir) / 'cerebrum'
        self.cerebrum_path.mkdir()

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    def test_workspace_creation(self):
        """Test creating a session workspace."""
        session_id = '20260205_120000'
        workspace = SessionWorkspace(session_id, self.cerebrum_path)
        workspace.create()

        # Check directory structure
        self.assertTrue(workspace.root.exists())
        self.assertTrue(workspace.analyses_dir.exists())
        self.assertTrue(workspace.parsed_dir.exists())
        self.assertTrue(workspace.memories_dir.exists())
        self.assertTrue(workspace.status_file.exists())

        # Check initial status
        status = workspace.get_status()
        self.assertEqual(status['status'], 'processing')
        self.assertEqual(status['session_id'], session_id)

    def test_status_updates(self):
        """Test updating session status."""
        workspace = SessionWorkspace('20260205_120000', self.cerebrum_path)
        workspace.create()

        # Update to complete
        workspace.mark_complete({'test': 'data'})
        status = workspace.get_status()
        self.assertEqual(status['status'], 'complete')
        self.assertEqual(status['test'], 'data')
        self.assertIn('completed_at', status)

        # Update to failed
        workspace.mark_failed('Test error')
        status = workspace.get_status()
        self.assertEqual(status['status'], 'failed')
        self.assertEqual(status['error'], 'Test error')
        self.assertIn('failed_at', status)

    def test_chunk_manifest(self):
        """Test chunk manifest initialization and updates."""
        workspace = SessionWorkspace('20260205_120000', self.cerebrum_path)
        workspace.create()

        # Initialize manifest with 5 chunks
        workspace.init_chunk_manifest(5)
        manifest = workspace.get_chunk_manifest()

        self.assertEqual(manifest['total_chunks'], 5)
        self.assertEqual(len(manifest['chunks']), 5)
        self.assertEqual(manifest['chunks']['1']['status'], 'pending')
        self.assertEqual(manifest['chunks']['5']['status'], 'pending')

        # Update chunk 1 to processing
        workspace.update_chunk_status(1, 'processing', {'worker_pid': 12345})
        manifest = workspace.get_chunk_manifest()
        self.assertEqual(manifest['chunks']['1']['status'], 'processing')
        self.assertEqual(manifest['chunks']['1']['worker_pid'], 12345)

        # Update chunk 1 to complete
        workspace.update_chunk_status(1, 'complete', {'patterns_count': 10})
        manifest = workspace.get_chunk_manifest()
        self.assertEqual(manifest['chunks']['1']['status'], 'complete')
        self.assertEqual(manifest['chunks']['1']['patterns_count'], 10)

        # Mark chunk 2 as failed
        workspace.update_chunk_status(2, 'failed', {'error': 'Timeout', 'attempts': 1})
        manifest = workspace.get_chunk_manifest()
        self.assertEqual(manifest['chunks']['2']['status'], 'failed')
        self.assertEqual(manifest['chunks']['2']['error'], 'Timeout')
        self.assertEqual(manifest['chunks']['2']['attempts'], 1)

    def test_logging(self):
        """Test session logging."""
        workspace = SessionWorkspace('20260205_120000', self.cerebrum_path)
        workspace.create()

        workspace.log('[TEST] First message')
        workspace.log('[TEST] Second message')

        # Check log file content
        log_content = workspace.log_file.read_text()
        self.assertIn('[TEST] First message', log_content)
        self.assertIn('[TEST] Second message', log_content)

    def test_get_session_workspaces(self):
        """Test retrieving all session workspaces."""
        # Create multiple workspaces
        session1 = SessionWorkspace('20260205_120000', self.cerebrum_path)
        session1.create()

        session2 = SessionWorkspace('20260205_130000', self.cerebrum_path)
        session2.create()

        session3 = SessionWorkspace('20260205_140000', self.cerebrum_path)
        session3.create()

        # Get all workspaces
        workspaces = get_session_workspaces(self.cerebrum_path)
        self.assertEqual(len(workspaces), 3)

        session_ids = {ws.session_id for ws in workspaces}
        self.assertIn('20260205_120000', session_ids)
        self.assertIn('20260205_130000', session_ids)
        self.assertIn('20260205_140000', session_ids)

    def test_get_active_sessions(self):
        """Test retrieving active sessions."""
        # Create workspaces with different statuses
        session1 = SessionWorkspace('20260205_120000', self.cerebrum_path)
        session1.create()
        # Leave as processing

        session2 = SessionWorkspace('20260205_130000', self.cerebrum_path)
        session2.create()
        session2.mark_complete()

        session3 = SessionWorkspace('20260205_140000', self.cerebrum_path)
        session3.create()
        session3.mark_failed('Test error')

        # Get active sessions (processing or complete, not failed)
        active = get_active_sessions(self.cerebrum_path)
        self.assertEqual(len(active), 2)

        active_ids = {ws.session_id for ws, status in active}
        self.assertIn('20260205_120000', active_ids)
        self.assertIn('20260205_130000', active_ids)
        self.assertNotIn('20260205_140000', active_ids)

    def test_empty_sessions_directory(self):
        """Test behavior when sessions directory doesn't exist."""
        workspaces = get_session_workspaces(self.cerebrum_path)
        self.assertEqual(workspaces, [])

        active = get_active_sessions(self.cerebrum_path)
        self.assertEqual(active, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
