#!/usr/bin/env python3
"""
Subconscious worker - processes session transcripts asynchronously.

This script runs as a detached background process after a session ends.
It analyzes the transcript, updates memories, and generates guidance.

Usage:
    python subconscious_worker.py <transcript_file> <cerebrum_path>
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

# Import terminal parser if available
try:
    import importlib.util
    parser_path = Path(__file__).parent / 'terminal_parser.py'
    if parser_path.exists():
        spec = importlib.util.spec_from_file_location("terminal_parser", parser_path)
        terminal_parser = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(terminal_parser)
        HAS_PARSER = True
    else:
        HAS_PARSER = False
except Exception:
    HAS_PARSER = False


def log(log_file: Path, message: str):
    """Write to processing log."""
    with open(log_file, 'a') as f:
        timestamp = datetime.now().isoformat()
        f.write(f"{timestamp} {message}\n")
        f.flush()


def load_transcript(filepath: Path) -> list:
    """Load JSONL transcript file."""
    events = []
    with open(filepath) as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
    return events


def find_terminal_recording(transcript_file: Path, cerebrum_path: Path) -> Optional[Path]:
    """
    Find terminal recording file matching transcript session ID.

    Args:
        transcript_file: Path to transcript JSONL file
        cerebrum_path: Path to cerebrum root

    Returns:
        Path to terminal recording if found, None otherwise
    """
    # Extract session ID from transcript filename
    # Format: transcript_YYYYMMDD_HHMMSS_*.jsonl -> terminal_YYYYMMDD_HHMMSS.txt
    import re
    match = re.search(r'transcript_(\d{8}_\d{6})', transcript_file.name)
    if not match:
        return None

    session_id = match.group(1)

    # Look for terminal recording
    recordings_dir = cerebrum_path / '.ai' / 'subconscious' / '.ai' / 'recordings'
    if not recordings_dir.exists():
        return None

    recording_file = recordings_dir / f'terminal_{session_id}.txt'
    if recording_file.exists():
        return recording_file

    return None


def process_transcript_basic(events: list, terminal_data: Optional[dict] = None) -> dict:
    """
    Basic transcript processing (placeholder for LLM processing).

    In Phase 3, this will call an LLM to analyze the transcript.
    For now, just extract simple statistics.

    Args:
        events: List of transcript events
        terminal_data: Optional parsed terminal recording data

    Returns:
        Analysis dictionary
    """
    session_start = next((e for e in events if e['type'] == 'session_start'), None)
    session_end = next((e for e in events if e['type'] == 'session_end'), None)

    analysis = {
        'event_count': len(events),
        'agent': session_start['metadata']['agent'] if session_start else 'unknown',
        'workspace': session_start['metadata']['workspace'] if session_start else 'unknown',
        'duration': session_end['metadata']['duration'] if session_end else 0,
        'session_id': session_start['metadata']['session_id'] if session_start else 'unknown'
    }

    # Add terminal recording data if available
    if terminal_data:
        analysis['has_terminal_recording'] = True
        analysis['terminal_text_length'] = len(terminal_data.get('raw_text', ''))
        analysis['terminal_messages'] = len(terminal_data.get('messages', []))

        # Include session metadata from terminal recording
        if 'metadata' in terminal_data:
            analysis['terminal_metadata'] = terminal_data['metadata']
    else:
        analysis['has_terminal_recording'] = False

    return analysis


def generate_guidance_basic(cerebrum_path: Path, analysis: dict):
    """
    Generate basic guidance file (placeholder for LLM-generated guidance).

    In Phase 5, this will use LLM to generate rich guidance.
    For now, just create a simple status file.
    """
    guidance_dir = cerebrum_path / '.ai' / 'subconscious' / '.ai'
    guidance_dir.mkdir(parents=True, exist_ok=True)

    guidance_file = guidance_dir / 'guidance.md'
    guidance_content = f"""---
last_updated: {datetime.now().isoformat()}
session_count: 1
---

# Subconscious Guidance

## Last Session Summary
- Agent: {analysis['agent']}
- Duration: {analysis['duration']:.1f}s
- Events captured: {analysis['event_count']}
- Workspace: {analysis['workspace']}

## Status
Subconscious processing is active. This guidance will be enhanced with:
- Pattern detection (Phase 3)
- Memory synthesis (Phase 4)
- Contextual guidance (Phase 5)

Session ID: {analysis['session_id']}
"""

    guidance_file.write_text(guidance_content)
    return guidance_file


def main():
    """Main worker process."""
    if len(sys.argv) < 3:
        print("Usage: python subconscious_worker.py <transcript_file> <cerebrum_path>")
        sys.exit(1)

    transcript_file = Path(sys.argv[1])
    cerebrum_path = Path(sys.argv[2])

    # Set up logging
    log_dir = cerebrum_path / '.ai' / 'subconscious' / '.ai'
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / 'processing.log'

    # Create lock file
    lockfile = log_dir / '.processing.lock'

    try:
        # Acquire lock
        lockfile.touch()
        log(log_file, f"[START] Processing {transcript_file.name}")

        # Load transcript
        if not transcript_file.exists():
            log(log_file, f"[ERROR] Transcript file not found: {transcript_file}")
            sys.exit(1)

        events = load_transcript(transcript_file)
        log(log_file, f"[LOAD] Loaded {len(events)} events")

        # Find and parse terminal recording if available
        terminal_data = None
        if HAS_PARSER:
            recording_file = find_terminal_recording(transcript_file, cerebrum_path)
            if recording_file:
                try:
                    terminal_data = terminal_parser.parse_terminal_recording(recording_file)
                    log(log_file, f"[PARSE] Parsed terminal recording: {len(terminal_data['raw_text'])} chars, {len(terminal_data['messages'])} messages")
                except Exception as e:
                    log(log_file, f"[WARN] Failed to parse terminal recording: {e}")

        # Process transcript (basic for now)
        analysis = process_transcript_basic(events, terminal_data)
        log(log_file, f"[ANALYZE] Session: {analysis['session_id']}, Duration: {analysis['duration']:.1f}s")
        if terminal_data:
            log(log_file, f"[ANALYZE] Terminal recording: {analysis['terminal_text_length']} chars")

        # TODO Phase 3: LLM processing for pattern detection
        # TODO Phase 4: Memory creation/updates

        # Generate guidance (basic for now)
        guidance_file = generate_guidance_basic(cerebrum_path, analysis)
        log(log_file, f"[GUIDANCE] Generated guidance: {guidance_file}")

        # Move processed transcript to processed directory
        processed_dir = cerebrum_path / '.ai' / 'subconscious' / '.ai' / 'processed'
        processed_dir.mkdir(parents=True, exist_ok=True)
        processed_file = processed_dir / transcript_file.name
        transcript_file.rename(processed_file)
        log(log_file, f"[ARCHIVE] Moved transcript to: {processed_file}")

        log(log_file, f"[COMPLETE] Processing complete")

    except Exception as e:
        log(log_file, f"[ERROR] {str(e)}")
        import traceback
        log(log_file, f"[ERROR] {traceback.format_exc()}")
        # Don't raise - just log and exit gracefully

    finally:
        # Always remove lock
        if lockfile.exists():
            lockfile.unlink()

    sys.exit(0)


if __name__ == '__main__':
    main()
