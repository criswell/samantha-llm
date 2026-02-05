#!/usr/bin/env python3
"""
Session workspace management for subconscious processing.

Each session gets an isolated workspace to prevent contention between
concurrent sessions and workers.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any


class SessionWorkspace:
    """
    Manages an isolated workspace for a single session's processing.

    Directory structure:
        sessions/{session_id}/
            ├── status.json          # Session processing status
            ├── manifest.json        # Chunk tracking
            ├── guidance.md          # Session-specific guidance
            ├── memories/            # Session-specific memories
            ├── analyses/            # Raw LLM output
            ├── parsed/              # Parsed conversation chunks
            └── processing.log       # Session-specific log
    """

    def __init__(self, session_id: str, cerebrum_path: Path):
        """
        Initialize session workspace.

        Args:
            session_id: Unique session identifier (YYYYMMDD_HHMMSS)
            cerebrum_path: Path to cerebrum root
        """
        self.session_id = session_id
        self.cerebrum_path = cerebrum_path

        # Session workspace root
        self.root = cerebrum_path / '.ai' / 'subconscious' / '.ai' / 'sessions' / session_id

        # Subdirectories
        self.analyses_dir = self.root / 'analyses'
        self.parsed_dir = self.root / 'parsed'
        self.memories_dir = self.root / 'memories'

        # Files
        self.status_file = self.root / 'status.json'
        self.manifest_file = self.root / 'manifest.json'
        self.guidance_file = self.root / 'guidance.md'
        self.log_file = self.root / 'processing.log'

    def create(self):
        """Create workspace directory structure."""
        self.root.mkdir(parents=True, exist_ok=True)
        self.analyses_dir.mkdir(exist_ok=True)
        self.parsed_dir.mkdir(exist_ok=True)
        self.memories_dir.mkdir(exist_ok=True)

        # Initialize status
        self.update_status('processing', {
            'created_at': datetime.now().isoformat(),
            'session_id': self.session_id
        })

    def update_status(self, status: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Update session status.

        Args:
            status: One of: processing, complete, failed
            metadata: Optional additional metadata
        """
        status_data = {
            'status': status,
            'updated_at': datetime.now().isoformat(),
            'session_id': self.session_id
        }

        if metadata:
            status_data.update(metadata)

        with open(self.status_file, 'w') as f:
            json.dump(status_data, f, indent=2)

    def get_status(self) -> Dict[str, Any]:
        """Get current session status."""
        if not self.status_file.exists():
            return {'status': 'unknown', 'session_id': self.session_id}

        with open(self.status_file) as f:
            return json.load(f)

    def init_chunk_manifest(self, total_chunks: int):
        """
        Initialize chunk processing manifest.

        Args:
            total_chunks: Total number of chunks to process
        """
        manifest = {
            'session_id': self.session_id,
            'total_chunks': total_chunks,
            'created_at': datetime.now().isoformat(),
            'chunks': {}
        }

        # Initialize all chunks as pending
        for i in range(1, total_chunks + 1):
            manifest['chunks'][str(i)] = {
                'status': 'pending',
                'attempts': 0,
                'created_at': datetime.now().isoformat()
            }

        with open(self.manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)

    def update_chunk_status(self, chunk_num: int, status: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Update chunk processing status.

        Args:
            chunk_num: Chunk number (1-indexed)
            status: One of: pending, processing, complete, failed
            metadata: Optional additional metadata (error message, worker_pid, etc.)
        """
        if not self.manifest_file.exists():
            return

        with open(self.manifest_file) as f:
            manifest = json.load(f)

        chunk_key = str(chunk_num)
        if chunk_key not in manifest['chunks']:
            manifest['chunks'][chunk_key] = {'attempts': 0}

        manifest['chunks'][chunk_key].update({
            'status': status,
            'updated_at': datetime.now().isoformat()
        })

        if metadata:
            manifest['chunks'][chunk_key].update(metadata)

        with open(self.manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)

    def get_chunk_manifest(self) -> Dict[str, Any]:
        """Get current chunk manifest."""
        if not self.manifest_file.exists():
            return {'chunks': {}}

        with open(self.manifest_file) as f:
            return json.load(f)

    def log(self, message: str):
        """
        Append message to session log.

        Args:
            message: Log message
        """
        with open(self.log_file, 'a') as f:
            timestamp = datetime.now().isoformat()
            f.write(f"{timestamp} {message}\n")
            f.flush()

    def mark_complete(self, metadata: Optional[Dict[str, Any]] = None):
        """Mark session processing as complete."""
        status_metadata = {'completed_at': datetime.now().isoformat()}
        if metadata:
            status_metadata.update(metadata)
        self.update_status('complete', status_metadata)

    def mark_failed(self, error: str):
        """Mark session processing as failed."""
        self.update_status('failed', {
            'error': error,
            'failed_at': datetime.now().isoformat()
        })


def get_session_workspaces(cerebrum_path: Path) -> list:
    """
    Get all session workspaces.

    Args:
        cerebrum_path: Path to cerebrum root

    Returns:
        List of SessionWorkspace objects
    """
    sessions_dir = cerebrum_path / '.ai' / 'subconscious' / '.ai' / 'sessions'
    if not sessions_dir.exists():
        return []

    workspaces = []
    for session_dir in sessions_dir.iterdir():
        if session_dir.is_dir():
            workspace = SessionWorkspace(session_dir.name, cerebrum_path)
            workspaces.append(workspace)

    return workspaces


def get_active_sessions(cerebrum_path: Path) -> list:
    """
    Get all active (processing or complete but not merged) sessions.

    Args:
        cerebrum_path: Path to cerebrum root

    Returns:
        List of (SessionWorkspace, status_dict) tuples
    """
    workspaces = get_session_workspaces(cerebrum_path)
    active = []

    for workspace in workspaces:
        status = workspace.get_status()
        if status['status'] in ('processing', 'complete'):
            active.append((workspace, status))

    return active
