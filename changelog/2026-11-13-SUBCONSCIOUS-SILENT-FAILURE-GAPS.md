# Subconscious Silent-Failure Design Gaps Closed

**Date**: 2026-11-13
**Purpose**: Make chunk failures visible and recoverable. Exposed by the
Sept 8-21 headless auth outage where 9 sessions / 530 chunks were silently
lost while every status surface reported healthy.

## The Four Gaps (from improvement item 8)

1. **All-failed sessions still reported "complete"**: the worker called
   `mark_complete()` unconditionally, so a session where every chunk failed
   showed as "Complete (Awaiting Merge)" in `bootstrap_status.py`.
2. **Documented auto-retry did not exist**: bootstrap.md claimed failed
   chunks "automatically retry"; the worker has no inline retry and
   `chunk_retry.py` was manual-only.
3. **chunk_retry could not reach archived sessions**: `retry_session` looked
   only in `sessions/`; after merge archived a workspace to `processed/<id>`,
   its failed chunks became unretryable in place.
4. **finalize inserted duplicate index entries**: no dedup by filename, and
   `merge_sessions.move_memories` copied a suffixed duplicate even when the
   on-disk file was byte-identical (the Sept backfill left 17 junk shells).

## Changes

### Honest session status (`subconscious_worker.py`, `session_workspace.py`)

- New `SessionWorkspace.chunk_failure_counts()` tallies complete/failed/total
  from the chunk manifest.
- Worker exit now picks the status from the counts:
  - all chunks complete (or no manifest, non-LLM path) -> `complete`
  - some complete, some failed -> `partial` (with counts + retry hint)
  - zero complete -> `failed` (with error + retry hint)
- `get_active_sessions()` now returns processing/complete/partial; new
  `get_failed_sessions()` returns failed. Partial sessions ride with active
  because they hold recoverable memories.

### Loud surfacing (`bootstrap_status.py`)

- `display_processing_status()` renders a `⚠️ PARTIAL` section and a
  `❌ FAILED` section with the retry command, and never shows the green
  "Complete (Awaiting Merge)" banner for a broken session.
- `get_status_summary()` gains `partial`, `failed`, and `needs_attention`
  keys so programmatic callers cannot mistake a broken session for healthy.
- `bootstrap.md` (Step 3.5 + subconscious section) now documents all three
  statuses and the "never merge a failed or partial session" rule. The
  inaccurate auto-retry claim is replaced with the manual retry workflow.

### Retry reaches archived sessions (`chunk_retry.py`, `session_workspace.py`)

- `SessionWorkspace` accepts a `base_dir` override.
- `retry_session()` resolves the session in `sessions/` first, then falls
  back to `processed/`, retrying archived failed chunks in place.

### Index dedup (`subconscious_worker.py`, `merge_sessions.py`)

- `finalize_session_memories()` updates the existing index entry in place
  when a memory file with the same name is re-finalized (including moving
  the entry between importance buckets) and recomputes `total_memories`
  from the index instead of incrementing per pass.
- `move_memories()` conflict policy: byte-identical destination = skip;
  different content = keep BOTH (suffixed with the session id).

## Tests

`test_integration.py` grows from 11 to 18 tests: chunk failure counting,
base_dir override, failed-session surfacing (summary + display), finalize
dedup/idempotence/importance-promotion, and the move_memories conflict
policy. Full suite: 108 passing.
