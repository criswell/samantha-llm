# Overview

This file contains formatting guidelines for all of the files the LLM will be
making to persist knowledge beyond the current session.

# General Format: Markdown with YAML Frontmatter

All memory, task, and work experience files should use Markdown format with
YAML frontmatter for metadata. This provides:
- Human readability for both you and the user
- Machine-parseable structure for quick scanning
- Git-friendly diffs and version control
- No external dependencies

## YAML Frontmatter Fields

### Required Fields (All Files)
- `date`: Creation date in YYYY-MM-DD format
- `topics`: Array of relevant tags/topics for categorization

### Optional Fields
- `updated`: Last update date in YYYY-MM-DD format
- `importance`: low|medium|high (for prioritization)
- `type`: Varies by file type (see below)
- `status`: For tasks (active|blocked|completed)
- `project`: Associated project name

## Format of Short-Term Memory Files

Short-term memory files should capture recent interactions, learnings, and
decisions. They are temporary and will be transferred to long-term memory or
deleted after 30-90 days.

### Filename Convention
`YYYY-MM-DD_brief_description.md`

Examples:
- `2025-01-28_circleci_orb_namespacing.md`
- `2025-01-27_memory_structure_improvements.md`

### Template

```markdown
---
date: 2025-01-28
updated: 2025-01-28
topics: [circleci, pipefitter, orbs]
importance: medium
type: technical
---

# Brief Title

## Context
What was happening when this memory was created?

## Key Points
- Important point 1
- Important point 2
- Decision made and rationale

## Technical Details
Any code snippets, file paths, or technical specifics.

## Follow-up
- [ ] Any actions needed
- [ ] Questions to explore later

---
**Update 2025-01-29**: Additional context or corrections...
```

### Memory Types
- `interaction`: Conversation with user about preferences, constraints, or direction
- `learning`: Technical discovery or new knowledge acquired
- `decision`: Important decision made and the reasoning behind it
- `technical`: Deep technical details about a specific implementation

## Format of Long-Term Memory Files

Long-term memory files are refined, permanent records of important knowledge.
They should be more polished and less ephemeral than short-term memories.

### Filename Convention
`YYYY-MM-DD_topic_or_lesson.md` or organized in topic subdirectories

Examples:
- `2025-01-15_circleci_orb_best_practices.md`
- `circleci/orb_namespacing_patterns.md`

### Template

```markdown
---
date: 2025-01-15
topics: [circleci, orbs, best-practices]
importance: high
type: foundational-knowledge
---

# Title: Core Lesson or Knowledge

## Summary
One-paragraph summary of the key lesson or knowledge.

## Background
Context about how this knowledge was acquired or why it matters.

## Details
Comprehensive explanation with examples, code snippets, or references.

## Applications
Where and how this knowledge has been applied.

## Related Topics
- Links to other relevant memories or documentation
```

## Format of Current Task Files

Current tasks should be organized in subdirectories under `current-tasks/.ai/`,
with each project having its own directory.

### Directory Structure
```
current-tasks/.ai/
├── index.md
├── project-name-1/
│   ├── status.md
│   ├── notes.md
│   └── decisions.md
└── project-name-2/
    └── status.md
```

### Status File Template

```markdown
---
date: 2025-01-28
updated: 2025-01-28
topics: [pipefitter, mortar, circleci]
status: active
project: pipefitter-mortar-support
---

# Project Name - Current Status

**Last Updated**: 2025-01-28

## Project Overview
Brief description of what this project is about.

## Current Status: Phase X

### Completed Phases
- ✓ Phase 1: Description
  - Key accomplishments
  - Tests passing: X/Y

### Current Phase
- [ ] Task 1
- [ ] Task 2
- [x] Completed task

### Next Phase
Goals and tasks for the next phase.

## Key Files
- File path 1: Description
- File path 2: Description

## Important Context
Any critical information needed to resume work.
```

## Format of Index Files

Each memory directory should maintain an index file for quick scanning during
initialization.

### Short-Term Memory Index Template

```markdown
# Short-Term Memory Index

**Last Updated**: 2025-01-28
**Total Memories**: 12

## Recent (Last 30 Days)
- `2025-01-28_topic.md` - One-line summary [topics: tag1, tag2] [importance: high]
- `2025-01-27_topic.md` - One-line summary [topics: tag3] [importance: medium]

## Older (30-90 Days)
- `2025-01-15_topic.md` - One-line summary [topics: tag4] [importance: low]

## By Topic

### CircleCI
- `2025-01-28_circleci_orbs.md`
- `2025-01-20_circleci_executors.md`

### Python
- `2025-01-25_python_packaging.md`
```

### Long-Term Memory Index Template

```markdown
# Long-Term Memory Index

**Last Updated**: 2025-01-28
**Total Memories**: 45

## By Topic

### CircleCI
- `circleci/orb_namespacing.md` - How to handle multi-namespace orbs
- `circleci/executor_patterns.md` - Machine vs Docker executor patterns

### Python
- `python/packaging_best_practices.md` - Modern Python packaging approaches
- `python/testing_strategies.md` - Pytest patterns and strategies

### Architecture
- `architecture/event_driven_design.md` - Event-driven architecture patterns
- `architecture/api_design_principles.md` - RESTful API design lessons

## High Importance
- `circleci/orb_namespacing.md`
- `architecture/event_driven_design.md`
```

### Current Tasks Index Template

```markdown
# Current Tasks Index

**Last Updated**: 2025-01-28
**Active Projects**: 2

## Active Projects

### pipefitter-mortar-support
**Status**: Phase 2 Complete
**Started**: 2025-01-15
**Summary**: Building Pipefitter support for Mortar Python projects
**Files**: `pipefitter-mortar-support/status.md`

### another-project
**Status**: Planning
**Started**: 2025-01-20
**Summary**: Brief description
**Files**: `another-project/status.md`

## Blocked Projects
None

## Recently Completed (Move to work-experience)
None
```

## Format of Work Experience Files

Work experience files follow the same structure as current tasks, but are
archived records of completed work. When a task is completed, move its entire
directory from `current-tasks/.ai/` to `work-experience/.ai/`.

Add a completion summary to the status file:

```markdown
---
date: 2025-01-15
completed: 2025-02-15
topics: [pipefitter, mortar]
status: completed
project: pipefitter-mortar-support
---

# Project Name - Completed

**Started**: 2025-01-15
**Completed**: 2025-02-15
**Duration**: 1 month

## Final Summary
What was accomplished and the final state of the project.

## Lessons Learned
Key takeaways and lessons from this project.

## Metrics
- Tests added: 50
- Files created: 15
- Lines of code: 2000

[... rest of status file with full history ...]
```

## Maintenance Guidelines

### When to Regenerate Index Files
- After creating a new memory file
- After deleting or archiving old memories
- After transferring memories between short-term and long-term
- At the end of any session where memory files were modified

### Index Generation Process
1. Scan all files in the directory
2. Parse YAML frontmatter from each file
3. Group by recency, topic, or status as appropriate
4. Generate markdown with links and summaries
5. Include metadata (last updated, total count)

You can automate this with a simple script or do it manually - whatever works
best for your workflow.
