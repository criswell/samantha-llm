## Session-Isolated Subconscious Processing

**Status**: ✅ Implemented and Tested
**Date**: 2026-02-05

### Overview

The subconscious worker now uses session-isolated workspaces to prevent conflicts between concurrent sessions and enable resilient chunk processing that survives laptop sleep.

### Architecture

```
.ai/subconscious/.ai/
├── sessions/                    # Active session workspaces
│   ├── 20260205_120000/         # Session 1 (isolated)
│   │   ├── status.json          # Session processing status
│   │   ├── manifest.json        # Chunk tracking
│   │   ├── guidance.md          # Session-specific guidance
│   │   ├── memories/            # Session-specific memories
│   │   ├── analyses/            # Raw LLM output
│   │   ├── parsed/              # Parsed conversation chunks
│   │   └── processing.log       # Session-specific log
│   │
│   └── 20260205_130000/         # Session 2 (concurrent!)
│       └── ...
│
├── processed/                   # Archived after merge
│   └── 20260205_120000/
│
├── guidance.md                  # Merged guidance (all sessions)
└── processing.log               # Global log (legacy)
```

### Key Features

✅ **Zero Contention**: Each session writes to isolated workspace
✅ **Concurrent Sessions**: Multiple sessions can process simultaneously
✅ **Laptop Sleep Resilient**: Failed chunks tracked and can be retried
✅ **Transparent Progress**: Bootstrap shows processing status
✅ **Fault Isolation**: One session's failure doesn't affect others
✅ **Graceful Merge**: Completed sessions merged asynchronously

### New Commands

#### 1. Check Processing Status

```bash
python bootstrap_status.py /path/to/cerebrum
```

Shows:
- Active sessions currently processing
- Chunk progress for each session
- Completed sessions awaiting merge
- Failed chunks needing retry

**Output Example:**
```
⏳ Subconscious Processing Status:
============================================================

📊 Currently Processing:
  • Session 20260205_120000
    Progress: 13/15 chunks (1 failed)
    Elapsed:  2h 15m
    Hint:     Run 'chunk_retry.py 20260205_120000 <cerebrum_path>' to retry

✅ Complete (Awaiting Merge):
  • Session 20260205_093000
    Completed: 2026-02-05T09:45:00

💡 Tip: Run 'merge_sessions.py <cerebrum_path>' to integrate these memories
```

#### 2. Retry Failed Chunks

```bash
python chunk_retry.py <session_id> /path/to/cerebrum
```

Retries failed chunks with exponential backoff:
- Attempt 1: immediate
- Attempt 2: wait 4s
- Attempt 3: wait 8s
- Max 3 attempts per chunk

**Use Case**: After laptop sleep interrupts processing

**Output Example:**
```
Session 20260205_120000: Retrying 2 failed chunks...
  Waiting 4s before retry (attempt 2)...
  Chunk 1: ✓ Success
  Chunk 14: ✓ Success

Retry complete: 2/2 chunks recovered
✓ All chunks complete! Session ready for merge.
```

#### 3. Merge Completed Sessions

```bash
python merge_sessions.py /path/to/cerebrum [--dry-run]
```

Consolidates completed sessions:
1. Merges session guidance into main guidance.md
2. Moves memories to cerebrum short-term memory
3. Archives session workspace

**Output Example:**
```
Found 2 completed session(s) to merge:
  - 20260205_093000 (completed: 2026-02-05T09:45:00)
  - 20260205_120000 (completed: 2026-02-05T10:30:00)

Merging sessions...
  1. Merging guidance files...✓ Merged 2 session(s) into guidance.md
  2. Processing 20260205_093000... ✓ (3 memories)
  2. Processing 20260205_120000... ✓ (5 memories)

✓ Merge complete!
  - Sessions merged: 2
  - Memories moved: 8
  - Archived to: .ai/subconscious/.ai/processed/
```

### Bootstrap Integration

Add to bootstrap process after loading critical memories:

```python
from bootstrap_status import display_processing_status

# Check for active subconscious processing
has_active = display_processing_status(cerebrum_path)

if has_active:
    print("\n💡 Some memories may still be processing. Check status above.")
```

### Workflow Examples

#### Scenario 1: Normal Processing (No Sleep)

1. Session ends → worker spawns
2. Worker creates session workspace
3. Processes chunks (updates manifest)
4. Marks session complete
5. User runs `merge_sessions.py`
6. Memories integrated into cerebrum

#### Scenario 2: Laptop Sleep During Processing

1. Session ends → worker spawns
2. Processing chunk 3/15...
3. **Laptop sleeps** → chunk 3 times out
4. Worker continues with chunks 4-15
5. Session status: 14/15 complete (chunk 3 failed)
6. User wakes laptop, runs `chunk_retry.py`
7. Chunk 3 retries successfully
8. Session now 15/15 complete
9. User runs `merge_sessions.py`
10. Memories integrated

#### Scenario 3: Concurrent Sessions

1. Session A ends at 12:00 → worker A spawns
2. Session B ends at 12:30 → worker B spawns
3. Both process in parallel (isolated workspaces)
4. No conflicts! Each writes to own directory
5. Both complete independently
6. Single `merge_sessions.py` merges both

### Testing

**Unit Tests (session_workspace):**
```bash
python test_session_workspace.py
# 7 tests, all passing ✅
```

**Integration Tests:**
```bash
python test_integration.py
# 3 tests, all passing ✅
```

### Migration Notes

**Backward Compatibility:**
- Old worker still works without session_workspace module
- Falls back to global logging
- New features gracefully degrade

**Gradual Migration:**
1. Deploy new code
2. Old sessions complete with old behavior
3. New sessions use session workspaces
4. No disruption!

### Future Enhancements

**Not Implemented (Manual Testing Required):**
- ⏳ Concurrent chunk workers (parallel chunk processing)
- ⏳ Proper file locking (fcntl.flock)
- ⏳ Automatic merge trigger
- ⏳ Real laptop sleep testing

**Ready for User Testing:**
- End laptop session mid-processing
- Let laptop sleep during chunk analysis
- Start new session while old one processes
- Run retry and merge commands

### Performance Impact

**Before:**
- Sequential chunk processing
- Global lock contention
- Session conflicts possible

**After:**
- Still sequential chunks (per session)
- Zero lock contention (isolated workspaces)
- Concurrent sessions safe
- Failed chunks recoverable

**Future with Concurrent Chunks:**
- 3-4x speedup possible
- Requires additional work queue implementation

### Files Changed

**New Files:**
- `session_workspace.py` - Workspace management
- `chunk_retry.py` - Retry failed chunks
- `merge_sessions.py` - Merge completed sessions
- `bootstrap_status.py` - Status display
- `test_session_workspace.py` - Unit tests
- `test_integration.py` - Integration tests
- `SESSION_ISOLATED_PROCESSING.md` - This doc

**Modified Files:**
- `subconscious_worker.py` - Uses session workspaces

### Success Criteria

✅ All unit tests pass (7/7)
✅ All integration tests pass (3/3)
✅ Session workspace creation works
✅ Chunk manifest tracking works
✅ Status display works
✅ Merge process works
✅ Backward compatible
⏳ Real laptop sleep test (user validation)
⏳ Real concurrent sessions test (user validation)

### Ready for Production

The automated testing confirms the system works correctly. The next step is manual validation:

1. **Test laptop sleep**: Start session, close laptop mid-processing, retry chunks
2. **Test concurrent sessions**: Start new session while old one processes
3. **Test merge**: Verify memories integrate correctly

After manual validation, system is production-ready! 🚀
