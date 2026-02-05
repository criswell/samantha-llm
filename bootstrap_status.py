#!/usr/bin/env python3
"""
Bootstrap status display - shows active subconscious processing status.

This module provides functions to display processing status during bootstrap,
so users know when analysis is happening and memories are pending.
"""

from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional

try:
    from session_workspace import SessionWorkspace, get_active_sessions
    HAS_WORKSPACE = True
except ImportError:
    HAS_WORKSPACE = False


def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable form.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., "2h 15m", "45m", "3m 20s")
    """
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s" if secs > 0 else f"{minutes}m"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"


def get_chunk_progress(workspace: SessionWorkspace) -> Tuple[int, int, int]:
    """
    Get chunk processing progress for a session.

    Args:
        workspace: SessionWorkspace instance

    Returns:
        Tuple of (complete_count, failed_count, total_count)
    """
    manifest = workspace.get_chunk_manifest()
    if not manifest or 'chunks' not in manifest:
        return (0, 0, 0)

    total = len(manifest['chunks'])
    complete = sum(1 for c in manifest['chunks'].values() if c['status'] == 'complete')
    failed = sum(1 for c in manifest['chunks'].values() if c['status'] == 'failed')

    return (complete, failed, total)


def calculate_elapsed_time(status: dict) -> Optional[float]:
    """
    Calculate elapsed time for a session.

    Args:
        status: Session status dict

    Returns:
        Elapsed time in seconds, or None if can't be calculated
    """
    created_at = status.get('created_at')
    if not created_at:
        return None

    try:
        created = datetime.fromisoformat(created_at)
        now = datetime.now()
        elapsed = (now - created).total_seconds()
        return elapsed
    except Exception:
        return None


def display_processing_status(cerebrum_path: Path) -> bool:
    """
    Display active subconscious processing status.

    Args:
        cerebrum_path: Path to cerebrum root

    Returns:
        True if there are active sessions, False otherwise
    """
    if not HAS_WORKSPACE:
        return False

    active_sessions = get_active_sessions(cerebrum_path)

    if not active_sessions:
        return False

    print("\n⏳ Subconscious Processing Status:")
    print("=" * 60)

    processing = []
    complete_ready = []

    for workspace, status in active_sessions:
        if status['status'] == 'processing':
            processing.append((workspace, status))
        elif status['status'] == 'complete':
            complete_ready.append((workspace, status))

    # Show processing sessions
    if processing:
        print("\n📊 Currently Processing:")
        for workspace, status in processing:
            # Get chunk progress
            complete, failed, total = get_chunk_progress(workspace)

            # Calculate elapsed time
            elapsed = calculate_elapsed_time(status)
            elapsed_str = format_duration(elapsed) if elapsed else "unknown"

            # Build status line
            progress = f"{complete}/{total} chunks"
            if failed > 0:
                progress += f" ({failed} failed)"

            print(f"  • Session {workspace.session_id}")
            print(f"    Progress: {progress}")
            print(f"    Elapsed:  {elapsed_str}")

            # Show helpful hint if there are failed chunks
            if failed > 0:
                print(f"    Hint:     Run 'chunk_retry.py {workspace.session_id} <cerebrum_path>' to retry")

    # Show completed sessions waiting for merge
    if complete_ready:
        print("\n✅ Complete (Awaiting Merge):")
        for workspace, status in complete_ready:
            completed_at = status.get('completed_at', 'unknown')
            print(f"  • Session {workspace.session_id}")
            print(f"    Completed: {completed_at}")

        print("\n💡 Tip: Run 'merge_sessions.py <cerebrum_path>' to integrate these memories")

    print("\n" + "=" * 60)

    return True


def get_status_summary(cerebrum_path: Path) -> dict:
    """
    Get a summary of subconscious processing status.

    Args:
        cerebrum_path: Path to cerebrum root

    Returns:
        Dict with status summary
    """
    if not HAS_WORKSPACE:
        return {'active': False}

    active_sessions = get_active_sessions(cerebrum_path)

    if not active_sessions:
        return {'active': False}

    processing_count = sum(1 for _, s in active_sessions if s['status'] == 'processing')
    complete_count = sum(1 for _, s in active_sessions if s['status'] == 'complete')

    return {
        'active': True,
        'processing': processing_count,
        'complete': complete_count,
        'total': len(active_sessions)
    }


def main():
    """Main entry point for status display."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python bootstrap_status.py <cerebrum_path>")
        print("\nDisplay subconscious processing status.")
        sys.exit(1)

    cerebrum_path = Path(sys.argv[1])

    if not cerebrum_path.exists():
        print(f"ERROR: Cerebrum path not found: {cerebrum_path}")
        sys.exit(1)

    has_active = display_processing_status(cerebrum_path)

    if not has_active:
        print("\n✓ No active subconscious processing")


if __name__ == '__main__':
    main()
