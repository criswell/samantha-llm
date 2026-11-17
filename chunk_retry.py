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

# Suspend guard module (Linux/systemd only). The actual re-exec happens at
# retry_session() entry, so an in-process CLI call is not exec-replaced at
# import time. Failure to import is non-fatal: log and continue unprotected.
try:
    import suspend_inhibit
except Exception:  # pragma: no cover - guard must never block retries
    suspend_inhibit = None
    print("[INHIBIT] WARN: suspend guard unavailable; continuing unprotected")

# Import session workspace
try:
    from session_workspace import SessionWorkspace
    HAS_WORKSPACE = True
except ImportError:
    HAS_WORKSPACE = False
    print("ERROR: session_workspace module not found")
    sys.exit(1)

# Import analyzer factory
try:
    analyzer_factory_path = Path(__file__).parent / 'analyzer_factory.py'
    spec = importlib.util.spec_from_file_location("analyzer_factory", analyzer_factory_path)
    analyzer_factory = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(analyzer_factory)
    HAS_ANALYZER = True
except Exception:
    HAS_ANALYZER = False


def create_best_analyzer(prompt_path: Path, output_dir: Optional[Path] = None, agent: str = 'claude'):
    """
    Create the best available analyzer with fallback logic.

    Priority is managed by analyzer_factory.

    Args:
        prompt_path: Path to analysis prompt
        output_dir: Optional directory for raw output
        agent: Agent name from session metadata (informational only)

    Returns:
        Configured analyzer instance

    Raises:
        RuntimeError: If no analyzer is available
    """
    if not HAS_ANALYZER:
        raise RuntimeError("Analyzer factory is not available")

    return analyzer_factory.create_best_analyzer(
        prompt_path,
        output_dir=output_dir,
        agent=agent
    )


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
    prompt_path: Path,
    agent: str = 'claude'
) -> bool:
    """
    Retry analyzing a failed chunk.

    Args:
        workspace: SessionWorkspace instance
        chunk_num: Chunk number to retry
        chunk_data: Chunk metadata from manifest
        prompt_path: Path to analysis prompt
        agent: Agent name from session metadata

    Returns:
        True if successful, False otherwise
    """
    workspace.log(f"[RETRY] Attempting chunk {chunk_num} (attempt {chunk_data.get('attempts', 0) + 1})")

    # Check if parsed chunk file exists
    session_id = workspace.session_id
    chunk_file = workspace.parsed_dir / f'parsed_{session_id}_chunk{chunk_num}.txt'

    # Fallback: check for 'unknown' session ID (legacy bug in original processing)
    if not chunk_file.exists():
        chunk_file_unknown = workspace.parsed_dir / f'parsed_unknown_chunk{chunk_num}.txt'
        if chunk_file_unknown.exists():
            chunk_file = chunk_file_unknown
            workspace.log(f"[RETRY] Using legacy chunk file: {chunk_file.name}")

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
        analyzer = create_best_analyzer(prompt_path, output_dir=workspace.analyses_dir, agent=agent)
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


def recombine_session_analyses(workspace, archived: bool):
    """Rebuild analysis_<sid>_full.md and _parsed.md from all chunk analyses.

    The worker's main analysis loop only combines chunk outputs when it
    finishes with a terminal state, so a session recovered by chunk_retry
    keeps stale combined files built from the pre-retry chunk subset (seen
    twice: sessions 20261113_172955 and 20261115_114055). This mechanically
    recomines what the worker would have written:
    - _full.md: every chunk's raw analysis under a '# Chunk N/total' header,
      joined by '---' separators (same format as the worker's combine step).
    - _parsed.md: each chunk parsed via the production AnalysisParser, merged
      with the same dedupe logic as _merge_chunk_results, rendered via
      AnalysisResult.to_markdown().
    """
    session_id = workspace.session_id
    analyses_dir = workspace.analyses_dir
    chunk_files = sorted(
        analyses_dir.glob(f'analysis_{session_id}_chunk*.md'),
        key=lambda p: int(p.stem.rsplit('chunk', 1)[1])
    )
    if not chunk_files:
        workspace.log("[RETRY] No chunk analyses found; skipping recombine")
        return

    total = len(chunk_files)

    # _full.md: raw section combine (worker's format)
    sections = []
    for i, chunk_file in enumerate(chunk_files, 1):
        sections.append(f"# Chunk {i}/{total}\n\n{chunk_file.read_text()}")
    full_file = analyses_dir / f'analysis_{session_id}_full.md'
    full_file.write_text("\n\n---\n\n".join(sections))
    workspace.log(f"[RETRY] Rebuilt {full_file.name} from {total} chunk analyses")

    # _parsed.md: parse + merge (same logic as subconscious_worker._merge_chunk_results)
    from conversation_analyzer import AnalysisParser, AnalysisResult

    results = [AnalysisParser.parse(f.read_text()) for f in chunk_files]

    def dedupe_list(items):
        seen = set()
        out = []
        for item in items:
            normalized = item.lower().strip()
            if normalized not in seen:
                seen.add(normalized)
                out.append(item)
        return out

    all_p, all_d, all_t, all_pr, all_l, summaries = [], [], [], [], [], []
    for i, r in enumerate(results, 1):
        all_p.extend(r.patterns)
        all_d.extend(r.decisions)
        all_t.extend(r.todos)
        all_pr.extend(r.preferences)
        all_l.extend(r.learnings)
        if r.summary:
            s = r.summary.strip()
            if len(s) > 500:
                s = s[:497] + '...'
            summaries.append(f"**Chunk {i}**: {s}")

    merged = AnalysisResult(
        patterns=dedupe_list(all_p),
        decisions=dedupe_list(all_d),
        todos=dedupe_list(all_t),
        preferences=dedupe_list(all_pr),
        learnings=dedupe_list(all_l),
        summary='\n\n'.join(summaries) if summaries else None,
    )
    parsed_file = analyses_dir / f'analysis_{session_id}_parsed.md'
    parsed_file.write_text(merged.to_markdown())
    workspace.log(
        f"[RETRY] Rebuilt {parsed_file.name} from {total} chunk analyses: "
        f"{len(merged.patterns)} patterns, {len(merged.decisions)} decisions, "
        f"{len(merged.todos)} TODOs"
    )


def restamp_session_complete(workspace):
    """Re-stamp session status to complete after full chunk recovery.

    The worker's main loop stamps terminal status only when IT finishes, so a
    session whose last chunks were recovered by chunk_retry stays 'partial'
    forever: merge_sessions.py skips it (only merges status=='complete') while
    bootstrap_status.py keeps shouting PARTIAL with stale counters. Once the
    manifest is all-complete, this re-stamp closes that loop.
    """
    counts = workspace.chunk_failure_counts()
    if counts['complete'] != counts['total'] or counts['total'] == 0:
        workspace.log(
            f"[RETRY] Skipping re-stamp: manifest shows {counts['complete']}/{counts['total']} complete"
        )
        return False

    from datetime import datetime
    status = workspace.get_status()
    workspace.mark_complete({
        'chunks_complete': counts['complete'],
        'chunks_failed': counts['failed'],
        'chunks_total': counts['total'],
        'recovered_by': 'chunk_retry',
        'note': 'All chunks complete after retry; status re-stamped complete post-recovery. '
                'Combined analysis files rebuilt from all chunk analyses.',
    })
    workspace.log(
        f"[RETRY] Re-stamped status '{status.get('status')}' -> 'complete' "
        f"({counts['complete']}/{counts['total']} chunks)"
    )
    return True


def retry_session(session_id: str, cerebrum_path: Path, max_retries: int = 3):
    """
    Retry all failed chunks in a session with exponential backoff.

    Args:
        session_id: Session ID to retry
        cerebrum_path: Path to cerebrum root
        max_retries: Maximum retry attempts per chunk
    """
    import json
    import glob

    # Suspend guard: re-exec under systemd-inhibit (Linux/systemd only) before
    # any chunk work. Standalone runs re-exec as this script; in-process CLI
    # calls re-exec the CLI into the same command (args re-parse, env guard
    # prevents loops) and land here again, now inhibited. A batch that can be
    # suspended is strictly better than a batch that never runs.
    if suspend_inhibit is not None:
        suspend_inhibit.inhibit_exec(log=print)

    # Look in the live sessions/ directory first, then fall back to the
    # processed/ archive. Gap fix (2026-11-13): retry_session previously only
    # looked in sessions/, so once merge_sessions archived a workspace to
    # processed/<id>, its failed chunks could never be retried in place. The
    # Sept 21 backfill had to reprocess full transcripts from scratch because
    # of exactly this blind spot.
    sessions_base = cerebrum_path / '.ai' / 'subconscious' / '.ai' / 'sessions'
    processed_base = cerebrum_path / '.ai' / 'subconscious' / '.ai' / 'processed'

    if (sessions_base / session_id).exists():
        workspace = SessionWorkspace(session_id, cerebrum_path, base_dir=sessions_base)
        archived = False
    elif (processed_base / session_id).exists():
        workspace = SessionWorkspace(session_id, cerebrum_path, base_dir=processed_base)
        archived = True
        print(f"Note: session {session_id} is archived under processed/; retrying in place.")
    else:
        print(f"ERROR: Session {session_id} not found (looked in sessions/ and processed/)")
        return

    workspace.log(f"[RETRY] Starting retry process for session {session_id}")

    # Find prompt file
    prompt_path = cerebrum_path / '.ai' / 'subconscious' / '.ai' / 'prompts' / 'analysis-prompt-v2.txt'
    if not prompt_path.exists():
        print(f"ERROR: Analysis prompt not found: {prompt_path}")
        return

    # Extract agent from processed transcript
    agent = 'claude'
    processed_transcript = cerebrum_path / '.ai' / 'subconscious' / '.ai' / 'processed' / f'transcript_{session_id}_*.jsonl'

    # Find the actual transcript file (glob pattern)
    transcript_files = list(glob.glob(str(processed_transcript)))
    if transcript_files:
        try:
            with open(transcript_files[0], 'r') as f:
                first_line = f.readline()
                if first_line.strip():
                    event = json.loads(first_line)
                    if event.get('type') == 'session_start':
                        agent = event.get('metadata', {}).get('agent', 'claude')
                        workspace.log(f"[RETRY] Detected session agent: {agent}")
        except Exception as e:
            workspace.log(f"[RETRY] Warning: Could not detect agent from transcript: {e}")

    print(f"Session agent: {agent}")

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

        success = retry_chunk(workspace, chunk_num, chunk_data, prompt_path, agent)

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
        recombine_session_analyses(workspace, archived)
        restamp_session_complete(workspace)
        if archived:
            print("  (Session is archived; run merge_sessions.py to re-merge the recovered memories.)")
        else:
            print("  Session re-stamped complete; run merge_sessions.py to integrate the memories.")
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
        print("ERROR: Analyzer factory not available")
        sys.exit(1)

    retry_session(session_id, cerebrum_path)


if __name__ == '__main__':
    main()
