# Migration Guide: JSON Index Format (2025-12-03)

**Status**: Active Migration  
**Applies To**: All Samantha Hartwell instances  
**Completion**: Once all instances have JSON indexes  
**Delete This File**: After migration complete (estimated 2025-12-10)

## What Changed

The cerebrum now supports **JSON index format** for better token efficiency:
- 30-35% token savings on index files (2,000-2,500 tokens per bootstrap)
- Structured data format eliminates prose while preserving all information
- Bootstrap process updated to prefer JSON, fall back to markdown

## Migration Steps

### 1. Pull Latest Changes
```bash
cd /path/to/doximity
git pull origin master
```

### 2. Verify Bootstrap Update
Check that `.ai-cerebrum/core_processes/bootstrap.md` mentions JSON indexes:
- Step 3 should reference `index.json` 
- Should have "Index File Formats" section

### 3. Generate JSON Indexes

You need to create JSON versions of your index files. The work instance has already done this, so you can:

**Option A: Copy from work instance** (if you have access)
```bash
# Copy JSON indexes from work instance
scp work-computer:.ai-cerebrum/short-term-memory/.ai/index.json .ai-cerebrum/short-term-memory/.ai/
scp work-computer:.ai-cerebrum/current-tasks/.ai/index.json .ai-cerebrum/current-tasks/.ai/
```

**Option B: Generate yourself**
Read the implementation guide and create JSON indexes based on your current markdown indexes:
- Read: `.ai-cerebrum/short-term-memory/.ai/2025-12-03_tier1_compression_implementation.md`
- Use the JSON schema documented there
- Convert your `index.md` files to `index.json` format
- Keep both formats in sync during transition

### 4. Test Bootstrap
Start a fresh session and verify:
- Bootstrap reads JSON indexes successfully
- All critical memories are surfaced
- Project context loads correctly
- No information is missing

### 5. Update This File
Once your migration is complete, update the status at the top of this file or delete it entirely.

## JSON Schema Reference

**Short-Term Memory** (`.ai-cerebrum/short-term-memory/.ai/index.json`):
```json
{
  "last_updated": "YYYY-MM-DD",
  "total_memories": N,
  "critical": [
    {
      "file": "filename.md",
      "summary": "Brief description",
      "importance": "high|medium|low",
      "references": N,
      "type": "quick-reference|decision|etc",
      "project": "optional-project-name"
    }
  ],
  "high_priority": [],
  "recent": {
    "high_importance": [...],
    "medium_importance": [...]
  },
  "stats": {...}
}
```

**Current Tasks** (`.ai-cerebrum/current-tasks/.ai/index.json`):
```json
{
  "last_updated": "YYYY-MM-DD",
  "active_count": N,
  "active": [
    {
      "name": "project-name",
      "status": "Phase X - Description",
      "started": "YYYY-MM-DD",
      "summary": "Description",
      "files": ["path/to/status.md"],
      "topics": ["topic1", "topic2"],
      "recent_progress": "Latest updates"
    }
  ],
  "blocked": [],
  "recently_completed": [...]
}
```

## Maintenance Going Forward

- **Keep both formats in sync** during transition period
- **Eventually deprecate markdown** once all instances use JSON
- **Update both files** when adding new memories or projects
- **Prefer JSON** for new index files (e.g., long-term memory)

## Questions?

Read the full implementation documentation:
- `.ai-cerebrum/short-term-memory/.ai/2025-12-03_tier1_compression_implementation.md`
- `.ai-cerebrum/current-tasks/.ai/cerebrum-optimization/status.md`

## Migration Status Tracking

| Instance | Status | Date | Notes |
|----------|--------|------|-------|
| Work computer (Sam) | ✅ Complete | 2025-12-03 | Original implementation |
| Personal computer | ⏳ Pending | - | Awaiting migration |

---

**After all instances migrate, delete this file and update memory_management.md to document JSON as the standard format.**
