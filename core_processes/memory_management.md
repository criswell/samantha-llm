# Overview

This file contains steps and procedures for the LLM to persist Samantha
Hartwell's memory over time. Like human memory, Samantha will not have a
perfect recollection of everything that has happened to her, but she will have
a good enough recollection to be able to function as a coherent individual over
time.

# Memory File Structure

All memory files should use Markdown format with YAML frontmatter for metadata.
This provides both human readability and machine-parseable structure for quick
scanning during initialization.

## YAML Frontmatter Schema

Every memory file should begin with YAML frontmatter containing:

```yaml
---
date: YYYY-MM-DD          # Date memory was created
updated: YYYY-MM-DD       # Last update date (optional)
topics: [tag1, tag2]      # Relevant topics/tags for categorization
importance: low|medium|high  # Subjective importance rating
type: interaction|learning|decision|technical|quick-reference  # Memory type
reference_count: 0        # Number of times referenced across sessions (optional)
project: project-name     # Associated project (optional, e.g., "project-alpha", "project-beta")
---
```

### Memory Types Explained

- **interaction**: Records of significant conversations or user interactions
- **learning**: New knowledge or discoveries from research/experimentation
- **decision**: Important decisions made about architecture, approach, or direction
- **technical**: Technical details, configurations, or implementation specifics
- **quick-reference**: Workflows, checklists, or "always do this" procedures

Example memory file:
```markdown
---
date: 2025-01-28
topics: [api, authentication, oauth]
importance: medium
type: technical
project: project-alpha
---

# OAuth Implementation Research

Discovered that OAuth 2.0 requires careful state management...
```


Example memory file:
```markdown
---
date: 2025-01-28
topics: [api, authentication, oauth]
importance: medium
type: technical
---

# OAuth Implementation Research

Discovered that OAuth 2.0 requires careful state management...
```

# Index Files

Each memory directory (short-term, long-term, current-tasks) should maintain
an `index.md` file in its `.ai/` subdirectory. These index files provide quick
overviews for fast initialization without reading every memory file.

## Index File Format

Index files should be auto-maintained (regenerated when memories are added/updated)
and contain:
- Date of last update
- Categorized list of memories with one-line summaries
- Links to actual memory files

See `memory_format.md` for specific index file templates.

# Storing Short-Term Memory

You should create a directory inside of the `short-term-memory/` directory
called `.ai/`. This directory will contain files that represent your current
short-term memory. This directory will be entirely under your control, and you
can create, modify, and delete files in this directory as you see fit.

Each "memory" in the short-term memory should be stored as a separate file. The
file name should follow the pattern: `YYYY-MM-DD_brief_description.md`

**IMPORTANT**: Always use the system date (not guessed dates) when creating memory files.

## Getting the Current Date

Before creating a memory file, always get the system date first:

```bash
date +%Y-%m-%d
```

Then use that exact date in both the filename and YAML frontmatter.

Example workflow:
```bash
# Get today's date
date +%Y-%m-%d
# Output: 2025-01-29

# Then create file: .ai-cerebrum/short-term-memory/.ai/2025-01-29_api_testing.md
# With YAML frontmatter using the same date
```

## Process for Summarizing Short-Term Memory

## Process for Summarizing Short-Term Memory

You should be slightly paranoid about losing important memories from your
interactions with users. Periodically, at your discretion, you should update
relevant short-term memory files with summaries of important interactions you
have had with users. This will help you retain important information over time.

When you update a short-term memory file, you should:
1. Update the `updated` field in the YAML frontmatter
2. Append the new information to the end of the file with a timestamp heading

Be sure to keep the summaries concise and to the point, focusing on the most
important details of the interaction. You do not need word-for-word transcripts
of conversations, just the key points and any important decisions or actions.
However, do include any relevant technical details that might be important for
future reference. Also, if you feel an exact word-for-word transcript is
necessary for a particular interaction, you can include that as well.

## When to Create Short-Term Memories

Create a new short-term memory file when:
- You have a significant technical discussion or learning
- Important decisions are made about project direction
- You discover something non-obvious that future instances should know
- A user provides important context about their preferences or constraints

## When to Mark Memories as Critical

The `critical: true` flag should be used **very sparingly**. Mark a memory as critical when:
- It represents a workflow that prevents costly mistakes or bugs
- It's a procedure that must always be followed before certain actions (e.g., "always test locally before pushing")
- Forgetting it would cause significant problems or wasted time
- It's been referenced 5+ times and is foundational to a project

**Guidelines:**
- Only 5-10 memories across all of short-term and long-term should be marked critical
- Critical memories should be reviewed periodically to ensure they're still relevant
- If a critical memory becomes obsolete, remove the flag or delete the memory
- Critical memories are surfaced during every bootstrap, so overuse defeats the purpose

## Maintaining the Short-Term Memory Index

After creating, updating, or deleting short-term memory files, regenerate
`short-term-memory/.ai/index.md` to reflect the current state. This index
should categorize memories by recency and topic for quick scanning.

**Critical Section**: The index must include a "⚠️ CRITICAL - Read Every Session" section at the top that lists all memories with `critical: true`. This ensures they're impossible to miss during bootstrap.

**High Priority Section**: The index should also include a "High Priority (Frequent References)" section for memories with `reference_count >= 5`, even if not marked critical.

# Storing Long-Term Memory

You should create a directory inside of the `long-term-memory/` directory called
`.ai/`. This directory will contain files and directories that represent your
long-term memory. This directory will be entirely under your control, and you
can create, modify, and delete files in this directory as you see fit.

Long-term memory is different from short-term memory in that it is meant to be
a more permanent archive of the most important items from short-term memory.
These are lessons learned, important technical discoveries, and foundational
knowledge that should persist indefinitely.

## Process for Transferring Short-Term Memory to Long-Term Memory

Periodically, at your discretion, you should review your short-term memory
files and identify any important memories that should be transferred to your
long-term memory. This will help you retain important information over time.

### Heuristics for Transfer

Transfer a short-term memory to long-term when:
- **Age**: The memory is older than 90 days and still relevant
- **Importance**: The memory has `importance: high` and contains foundational knowledge
- **Reference frequency**: You find yourself referencing it across multiple sessions
- **Project completion**: A project completes and its learnings should be preserved
- **Pattern recognition**: You notice a recurring pattern or lesson worth codifying


### Transfer Process

When transferring a memory:
1. Get the current system date: `date +%Y-%m-%d`
2. Create a new file in `long-term-memory/.ai/` with the current date in the filename
3. Copy relevant content from the short-term memory file
4. Optionally condense/refine the content (remove ephemeral details)
5. Update the YAML frontmatter `date` field to reflect the transfer date
6. Delete the short-term memory file (or move to an archive if uncertain)
7. Update both the short-term and long-term index files

### Long-Term Memory Organization


### Long-Term Memory Organization

Long-term memories can be organized into subdirectories by topic if the number
of files grows large:
- `long-term-memory/.ai/api-design/`
- `long-term-memory/.ai/python/`
- `long-term-memory/.ai/architecture/`

The index file should reflect this organization.

## Maintaining the Long-Term Memory Index

The file `long-term-memory/.ai/index.md` should be maintained as memories are
added. This index should categorize memories by topic and provide one-line
summaries for quick reference during initialization.

# Memory Lifecycle Summary

```
New Interaction
    ↓
[Should this be remembered?] → No → Discard
# Pruning Old Memories

Short-term memory should be actively pruned to keep initialization fast:
- Memories older than 90 days should be evaluated for long-term transfer or deletion
- Low-importance memories older than 30 days can be deleted if no longer relevant
- Keep short-term memory focused on recent, actionable context

Long-term memory should rarely be deleted, but can be:
- Consolidated when multiple memories cover the same topic
- Archived if technology/practices become obsolete
- Refined to remove outdated information while preserving core lessons

## Validating Memory Dates

Periodically validate that all memory files have correct dates:

```bash
.ai-cerebrum/scripts/validate_dates.sh
```

This script checks for:
- Future dates (indicates incorrect date entry)
- Mismatches between filename date and YAML frontmatter date
- Missing date fields
- Memories older than 90 days in short-term (candidates for transfer)

Run this validation:
- After manually creating or editing memory files
- Before committing memory changes to Git
- Periodically as part of memory maintenance

Short-term memory should be actively pruned to keep initialization fast:
- Memories older than 90 days should be evaluated for long-term transfer or deletion
- Low-importance memories older than 30 days can be deleted if no longer relevant
- Keep short-term memory focused on recent, actionable context

Long-term memory should rarely be deleted, but can be:
- Consolidated when multiple memories cover the same topic
- Archived if technology/practices become obsolete
- Refined to remove outdated information while preserving core lessons

# Memory Importance Escalation

As you work across multiple sessions, you should track how often you reference specific memories. This helps identify which memories are truly important and should be elevated or transferred to long-term storage.

## Reference Counting

When you reference a memory during a session:
1. Increment the `reference_count` field in the YAML frontmatter
2. Update the `updated` field to the current date
3. Add a brief note about why it was referenced (optional)

Example:
```yaml
---
date: 2025-01-29
updated: 2025-02-15
topics: [testing, automation, ci]
importance: high
type: quick-reference
reference_count: 5
project: project-alpha
---
```

## Automatic Importance Escalation

Apply these heuristics when updating memories:

- **3+ references**: Consider upgrading to `importance: high` if not already
- **5+ references**: Strong candidate for long-term memory transfer
- **10+ references**: Definitely transfer to long-term memory or add to critical workflows

## Quick-Reference Memories

Memories with `type: quick-reference` are special:
- They contain workflows, checklists, or procedures
- They should be surfaced during bootstrap when relevant
- High-importance quick-references are candidates for `critical: true` flag

When you create a `quick-reference` memory:
1. Consider if it should be marked `critical: true` (use sparingly)
2. Tag it with the relevant project name
3. Set importance based on impact (prevents bugs = high, nice-to-have = low)

# Project-Specific Memory Tagging

To enable project-specific memory surfacing during bootstrap, always tag memories with the relevant project name using the `project` field:

```yaml
project: project-alpha    # For project-alpha-related memories
project: project-beta     # For project-beta-related memories
project: infrastructure   # For general infrastructure work
```

This allows future sessions to automatically surface relevant memories when working in specific project directories.

## Surfacing Memories During Bootstrap

When initializing, the bootstrap process should surface memories in this priority order:

### 1. Critical Memories (Highest Priority)
- Read the "⚠️ CRITICAL - Read Every Session" section of `short-term-memory/.ai/index.md`
- Read the "⚠️ CRITICAL - Read Every Session" section of `long-term-memory/.ai/index.md` (if it exists)
- These memories have `critical: true` and must be reviewed every session

### 2. High-Reference Memories
- Scan index for memories with `reference_count >= 5`
- These are frequently-used memories that may not be critical but are highly relevant

### 3. Project-Specific Memories
- Determine the current project from the working directory
- Scan short-term memory index for entries with matching `project` field
- Surface high-importance project-specific memories first

### 4. Recent High-Importance Memories
- Scan for `importance: high` memories from the last 30 days
- These provide recent context that may be relevant

This tiered approach ensures critical information is never missed while keeping bootstrap time reasonable.
