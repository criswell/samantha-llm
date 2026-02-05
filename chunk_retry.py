#!/usr/bin/env python3
"""
Chunk retry system for handling failed chunks.

This script can be run independently to retry failed chunks in a session,
which is useful after laptop sleep or transient errors.
"""

import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Optional
import importlib.util

# Import session workspace
try:
    from session_workspace import SessionWorkspace
    HAS_WORKSPACE = True
except ImportError:
    HAS_WORKSPACE = False
    print("ERROR: session_workspace module not found")
    sys.exit(1)

# Import analyzer
try:
    analyzer_path = Path(__file__).parent / 'claude_analyzer.py'
    spec = importlib.util.spec_from_file_location("claude_analyzer", analyzer_path)
    claude_analyzer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(claude_analyzer)
    HAS_ANALYZER = True
except Exception:
    HAS_ANALYZER = False


def get_failed_chunks(workspace: SessionWorkspace) -> list:
    """
    Get list of failed chunks that can be retried.

    Args:
        workspace: SessionWorkspace instance

    Returns:
        List of (chunk_num, chunk_data) tuples for failed chunks
    """
    manifest = workspace.get_chunk_manifest()
    if not manifest or 'chunks' not in manifest:
        return []

    failed = []
    for chunk_id, chunk_data in manifest['chunks'].items():
        if chunk_data['status'] == 'failed':
            attempts = chunk_data.get('attempts', 0)
            # Only retry if under max attempts (default: 3)
            if attempts < 3:
                failed.append((int(chunk_id), chunk_data))

    # Sort by chunk number
    failed.sort(key=lambda x: x[0])
    return failed


def retry_chunk(
    workspace: SessionWorkspace,
    chunk_num: int,
    chunk_data: dict,
    prompt_path: Path
) -> bool:
    """
    Retry analyzing a failed chunk.

    Args:
        workspace: SessionWorkspace instance
        chunk_num: Chunk number to retry
        chunk_data: Chunk metadata from manifest
        prompt_path: Path to analysis prompt

    Returns:
        True if successful, False otherwise
    """
    workspace.log(f"[RETRY] Attempting chunk {chunk_num} (attempt {chunk_data.get('attempts', 0) + 1})")

    # Check if parsed chunk file exists
    session_id = workspace.session_id
    chunk_file = workspace.parsed_dir / f'parsed_{session_id}_chunk{chunk_num}.txt'

    if not chunk_file.exists():
        workspace.log(f"[RETRY] ERROR: Chunk file not found: {chunk_file}")
        return False

    # Update attempt count
    workspace.update_chunk_status(chunk_num, 'processing', {
        'started_at': datetime.now().isoformat(),
        'attempts': chunk_data.get('attempts', 0) + 1
    })

    try:
        # Analyze chunk
        analyzer = claude_analyzer.create_analyzer(prompt_path, output_dir=workspace.analyses_dir)
        result = analyzer.analyze(chunk_file)

        workspace.log(f"[RETRY] Chunk {chunk_num} complete: {len(result.patterns)} patterns, {len(result.decisions)} decisions")

        # Mark as complete
        workspace.update_chunk_status(chunk_num, 'complete', {
            'completed_at': datetime.now().isoformat(),
            'patterns_count': len(result.patterns),
            'decisions_count': len(result.decisions),
            'retried': True
        })

        return True

    except Exception as e:
        workspace.log(f"[RETRY] ERROR: Chunk {chunk_num} failed again: {e}")

        # Mark as failed with incremented attempt count
        workspace.update_chunk_status(chunk_num, 'failed', {
            'failed_at': datetime.now().isoformat(),
            'error': str(e),
            'attempts': chunk_data.get('attempts', 0) + 1
        })

        return False


def retry_session(session_id: str, cerebrum_path: Path, max_retries: int = 3):
    """
    Retry all failed chunks in a session with exponential backoff.

    Args:
        session_id: Session ID to retry
        cerebrum_path: Path to cerebrum root
        max_retries: Maximum retry attempts per chunk
    """
    workspace = SessionWorkspace(session_id, cerebrum_path)

    # Check if session exists
    if not workspace.root.exists():
        print(f"ERROR: Session {session_id} not found")
        return

    workspace.log(f"[RETRY] Starting retry process for session {session_id}")

    # Find prompt file
    prompt_path = cerebrum_path / '.ai' / 'subconscious' / '.ai' / 'prompts' / 'analysis-prompt-v2.txt'
    if not prompt_path.exists():
        print(f"ERROR: Analysis prompt not found: {prompt_path}")
        return

    # Get failed chunks
    failed_chunks = get_failed_chunks(workspace)

    if not failed_chunks:
        workspace.log("[RETRY] No failed chunks to retry")
        print(f"Session {session_id}: No failed chunks found")
        return

    workspace.log(f"[RETRY] Found {len(failed_chunks)} failed chunks to retry")
    print(f"\nSession {session_id}: Retrying {len(failed_chunks)} failed chunks...")

    # Retry each failed chunk with exponential backoff
    success_count = 0
    for chunk_num, chunk_data in failed_chunks:
        attempt = chunk_data.get('attempts', 0) + 1

        # Exponential backoff: 2^attempt seconds (but cap at 60 seconds for testing)
        if attempt > 1:
            wait_time = min(2 ** attempt, 60)
            print(f"  Waiting {wait_time}s before retry (attempt {attempt})...")
            workspace.log(f"[RETRY] Waiting {wait_time}s before chunk {chunk_num} (attempt {attempt})")
            time.sleep(wait_time)

        print(f"  Chunk {chunk_num}: ", end='', flush=True)

        success = retry_chunk(workspace, chunk_num, chunk_data, prompt_path)

        if success:
            print("✓ Success")
            success_count += 1
        else:
            print("✗ Failed")

    # Summary
    print(f"\nRetry complete: {success_count}/{len(failed_chunks)} chunks recovered")
    workspace.log(f"[RETRY] Complete: {success_count}/{len(failed_chunks)} chunks recovered")

    # Check if session is now complete
    manifest = workspace.get_chunk_manifest()
    all_complete = all(
        chunk['status'] == 'complete'
        for chunk in manifest['chunks'].values()
    )

    if all_complete:
        print("✓ All chunks complete! Session ready for merge.")
        workspace.log("[RETRY] All chunks now complete")
        # Don't auto-mark as complete - let the merge process do that
    else:
        remaining_failed = len([
            c for c in manifest['chunks'].values()
            if c['status'] == 'failed'
        ])
        print(f"⚠ {remaining_failed} chunks still failed (max retries reached)")


def main():
    """Main entry point for chunk retry."""
    if len(sys.argv) < 3:
        print("Usage: python chunk_retry.py <session_id> <cerebrum_path>")
        print("\nRetry failed chunks in a session (useful after laptop sleep).")
        print("\nExample:")
        print("  python chunk_retry.py 20260205_120000 /path/to/cerebrum")
        sys.exit(1)

    session_id = sys.argv[1]
    cerebrum_path = Path(sys.argv[2])

    if not HAS_ANALYZER:
        print("ERROR: Claude analyzer not available")
        sys.exit(1)

    retry_session(session_id, cerebrum_path)


if __name__ == '__main__':
    main()
