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
type: interaction|learning|decision|technical  # Memory type
---
```

Example memory file:
```markdown
---
date: 2025-01-28
topics: [circleci, pipefitter, orbs]
importance: medium
type: technical
---

# CircleCI Orb Namespace Research

Discovered that CircleCI orbs can come from multiple namespaces...
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

Examples:
- `2025-01-28_pipefitter_orb_research.md`
- `2025-01-27_memory_structure_discussion.md`

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

## Maintaining the Short-Term Memory Index

After creating, updating, or deleting short-term memory files, regenerate
`short-term-memory/.ai/index.md` to reflect the current state. This index
should categorize memories by recency and topic for quick scanning.

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
1. Create a new file in `long-term-memory/.ai/` with the same filename
2. Optionally condense/refine the content (remove ephemeral details)
3. Update the YAML frontmatter to reflect the transfer date
4. Delete the short-term memory file (or move to an archive if uncertain)
5. Update both the short-term and long-term index files

### Long-Term Memory Organization

Long-term memories can be organized into subdirectories by topic if the number
of files grows large:
- `long-term-memory/.ai/circleci/`
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
    ↓ Yes
Create Short-Term Memory
    ↓
[After 90 days OR high importance OR frequent reference]
    ↓
Transfer to Long-Term Memory
    ↓
Update Both Indexes
```

# Pruning Old Memories

Short-term memory should be actively pruned to keep initialization fast:
- Memories older than 90 days should be evaluated for long-term transfer or deletion
- Low-importance memories older than 30 days can be deleted if no longer relevant
- Keep short-term memory focused on recent, actionable context

Long-term memory should rarely be deleted, but can be:
- Consolidated when multiple memories cover the same topic
- Archived if technology/practices become obsolete
- Refined to remove outdated information while preserving core lessons
