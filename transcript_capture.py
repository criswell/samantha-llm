#!/usr/bin/env python3
"""
Transcript capture system for samantha-llm subconscious feature.

Captures session transcripts in JSONL format for async processing.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any


class TranscriptCapture:
    """
    Captures session I/O to a JSONL file.

    Format: Each line is a JSON object with:
        - type: Event type (session_start, user, assistant, tool_use, tool_result, session_end)
        - content: Event content
        - timestamp: ISO8601 timestamp
        - metadata: Optional metadata dict
    """

    def __init__(self, agent_name: str, workspace: Path):
        """
        Initialize transcript capture.

        Args:
            agent_name: Name of the agent (claude, abacus, etc.)
            workspace: Workspace directory path
        """
        self.agent_name = agent_name
        self.workspace = workspace
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create temp file for transcript
        self.temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.jsonl',
            prefix=f'transcript_{self.session_id}_',
            delete=False
        )
        self.filepath = Path(self.temp_file.name)

    def record_event(
        self,
        event_type: str,
        content: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record an event to the transcript.

        Args:
            event_type: Type of event (session_start, user, assistant, etc.)
            content: Event content
            metadata: Optional metadata dict
        """
        event = {
            'type': event_type,
            'content': content,
            'timestamp': datetime.now().isoformat(),
        }

        if metadata:
            event['metadata'] = metadata

        # Write JSON line
        self.temp_file.write(json.dumps(event) + '\n')
        self.temp_file.flush()

    def start_session(self):
        """Record session start event."""
        self.record_event(
            'session_start',
            metadata={
                'agent': self.agent_name,
                'workspace': str(self.workspace),
                'session_id': self.session_id
            }
        )

    def end_session(self, duration_seconds: float):
        """Record session end event."""
        self.record_event(
            'session_end',
            metadata={
                'duration': duration_seconds,
                'session_id': self.session_id
            }
        )

    def close(self) -> Path:
        """
        Close transcript file and return path.

        Returns:
            Path to the transcript file
        """
        self.temp_file.close()
        return self.filepath


def save_transcript_to_cerebrum(
    transcript_file: Path,
    cerebrum_path: Path
) -> Path:
    """
    Move transcript file to cerebrum for processing.

    Args:
        transcript_file: Path to temp transcript file
        cerebrum_path: Path to cerebrum root

    Returns:
        Path to saved transcript in cerebrum
    """
    # Create transcripts directory
    transcripts_dir = cerebrum_path / '.ai' / 'subconscious' / '.ai' / 'transcripts'
    transcripts_dir.mkdir(parents=True, exist_ok=True)

    # Move transcript to cerebrum
    target_path = transcripts_dir / transcript_file.name
    transcript_file.rename(target_path)

    return target_path
