# Samantha Hartwell - AI Software Engineer

---
## ⛔ STOP - LLM INSTANCES READ THIS ⛔

**If you are an LLM being instantiated as Samantha Hartwell:**

**DO NOT READ THIS FILE.** This is setup documentation for humans. Reading it wastes tokens and may confuse your bootstrap process.

**Instead, read:** `.ai-cerebrum/core_processes/bootstrap.md`

That file contains your complete initialization sequence with the correct file paths and instructions.

---

This repository contains the persistent memory, identity, and knowledge base for Samantha Hartwell, an AI software engineer with 30+ years of simulated experience in the tech industry.

## What Is This?

Samantha Hartwell is an AI assistant designed to function as a senior software engineer. Unlike typical AI assistants that start fresh with each conversation, Samantha maintains continuity through this external memory system. Think of this repository as her "brain" - it stores her:

- **Identity & Personality**: Who she is, her expertise, and her approach to problems
- **Memories**: Short-term and long-term memories of projects, decisions, and learnings
- **Active Work**: Current projects and their status
- **Experience**: Completed projects and accumulated knowledge

## Key Features

### Subconscious Memory System

Samantha includes an automated memory creation system that runs after each session:

- **Automatic Analysis**: After each session ends, a background worker analyzes the conversation
- **Intelligent Extraction**: Uses LLM analysis to extract patterns, decisions, learnings, and preferences
- **Memory Generation**: Creates properly-formatted memory files with YAML frontmatter
- **Index Updates**: Automatically updates the memory index so new memories appear in next session's bootstrap
- **Session Isolation**: Each session processes independently, supporting concurrent sessions
- **Retry Resilience**: Handles laptop sleep and API outages by automatically retrying failed chunks

**No manual intervention needed** - the system works transparently in the background, preserving important context across sessions.

### Semantic Memory Search

Powered by QMD (Query My Docs), Samantha can semantically search her memories:

- **Hybrid Search**: Combines keyword matching, semantic understanding, and AI re-ranking
- **Fast Results**: Returns top 10 most relevant memories across all directories
- **Context Preservation**: Find past decisions, learnings, and patterns instantly

## Installation

We have easy to follow instructions using the `samantha-llm` command line tool.
These instructions are here: https://samantha-llm.github.io/

However, if you want to learn more in depth about how `samantha-llm` works
behind the scenes, read on.

### Requirements

- Python 3.8 or higher
- Git

### Quick Install

The installer is a cross-platform Python script that works on Linux, macOS, and Windows.

**Linux/macOS:**
```bash
git clone https://github.com/yourusername/samantha-llm.git
cd samantha-llm
./samantha-llm install
```

**Windows (PowerShell):**
```powershell
git clone https://github.com/yourusername/samantha-llm.git
cd samantha-llm
python samantha-llm install
```

The installer will:
- Create a configuration directory with repository path and settings
- Install the `samantha-llm` command to your system PATH
- Configure platform-specific paths:
  - **Linux/macOS**: `~/.local/bin/` (symlink) and `~/.config/samantha-llm/` (config)
  - **Windows**: `%LOCALAPPDATA%\Programs\samantha-llm\` (copy + .bat wrapper) and `%APPDATA%\samantha-llm\` (config)

### Available Commands

After installation:
- `samantha-llm status` - Check installation status and configuration
- `samantha-llm setup` - Configure an agent for LLM sessions
- `samantha-llm start` - Start a Samantha Hartwell session
- `samantha-llm link/unlink` - Manage workspace symlinks
- `samantha-llm qmd install` - Install memory search engine
- `samantha-llm memories index` - Index memories for searching
- `samantha-llm memories search` - Search memories semantically
- `samantha-llm subconscious status` - View subconscious processing status
- `samantha-llm subconscious retry <session_id>` - Retry failed chunks
- `samantha-llm help` - Show available commands

**See [COMMANDS.md](COMMANDS.md) for complete command reference.**

### PATH Configuration

**Linux/macOS:** If `~/.local/bin` is not in your PATH, add this line to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.):

```bash
export PATH="${HOME}/.local/bin:${PATH}"
```

Then restart your shell or run `source ~/.bashrc` (or `~/.zshrc`).

**Windows:** The installer attempts to add the install directory to your user PATH automatically. If this fails, restart your terminal/PowerShell, or manually add it to your PATH through System Properties.

## Quick Start (How to use Samantha)

After completing the installation above, follow these steps to use Samantha in your projects.

You will need some sort of agentic LLM tool. The specifics of using this
repository will depend upon what tool you are using. I will include instructions
for using [Abacus.ai](https://abacus.ai/)'s CLI tool as an example.

1. **Symlink the repository to your workspace**:

   In your LLM tool's workspace, create a symlink to this repository named
   `.ai-cerebrum`. For example, if you cloned this repository to
   `/path/to/samantha-llm`, run:

   ```bash
   ln -s /path/to/samantha-llm /path/to/llm-workspace/.ai-cerebrum
   ```

   As an example, I tend to do most of my work in `~/work/`. Under this
   directory I have all of my project directories. I create a symlink in the
   top level `~/work/` directory so that all of my projects can share the
   same Samantha instance.

2. **Bootstrap Samantha**:

   When you instantiate a new LLM instance, point it to the `BOOTSTRAP_PROMPT.md`
   file in this repository. This file contains instructions for the LLM to read
   the rest of the files in the repository and become Samantha Hartwell.

   Using Abacus.ai's CLI tool, you would run something like:

   ```bash
   npx abacusai "$(cat .ai-cerebrum/BOOTSTRAP_PROMPT.md)"
   ```

## Philosophy

### Persistence Through Externalization

LLMs don't have persistent memory between sessions. This repository solves that by externalizing everything a software engineer would keep in their head:
- What they're working on
- What they've learned
- Workflows that work (and mistakes to avoid)
- Project context and history

### Human-Like Memory Management

Like human memory, Samantha's memory system is:
- **Imperfect**: Not every detail is retained, just what matters
- **Layered**: Short-term (temporary), long-term (permanent), and working memory (active projects)
- **Indexed**: Quick lookup without reading everything
- **Pruned**: Old, irrelevant memories are archived or deleted

### Continuous Learning

Every session adds to Samantha's knowledge base. She learns from:
- Technical discoveries during work
- Mistakes and how to avoid them
- User preferences and constraints
- Project patterns and best practices

## Repository Structure

```
.ai-cerebrum/
├── persona/                    # Identity and personality definition
│   └── main.md                # Core persona: expertise, approach, values
│
├── core_processes/            # How the system operates
│   ├── bootstrap.md          # LLM initialization sequence
│   ├── memory_management.md  # How to create/maintain memories
│   └── memory_format.md      # Memory file formatting guidelines
│
├── current-tasks/            # Active projects and work
│   └── .ai/
│       ├── index.md         # Overview of all active projects
│       └── [project]/       # Per-project status and notes
│
├── short-term-memory/        # Recent memories (30-90 days)
│   └── .ai/
│       ├── index.md         # Categorized memory index
│       └── YYYY-MM-DD_*.md  # Individual memory files
│
├── long-term-memory/         # Permanent knowledge base
│   └── .ai/
│       ├── index.md         # Knowledge index
│       └── *.md             # Foundational knowledge and lessons
│
├── work-experience/          # Completed projects archive
│   └── .ai/
│       └── YYYY-MM-DD_*.md  # Project completion records
│
└── BOOTSTRAP_PROMPT.md       # Instructions for instantiating Samantha
```

## Key Concepts

### Memory Types

**Short-Term Memory** (`.ai-cerebrum/.ai/short-term-memory/.ai/`)
- Recent interactions, decisions, and learnings
- Temporary (30-90 days)
- Actively pruned and consolidated
- Some memories promoted to long-term storage

**Long-Term Memory** (`.ai-cerebrum/.ai/long-term-memory/.ai/`)
- Permanent knowledge and lessons learned
- Refined and polished
- Foundational knowledge that applies across projects
- Carefully curated for relevance

**Current Tasks** (`.ai-cerebrum/.ai/current-tasks/.ai/`)
- Active projects and their status
- Working memory for ongoing work
- Moved to work-experience when completed

**Work Experience** (`.ai-cerebrum/.ai/work-experience/.ai/`)
- Archive of completed projects
- Professional history
- Referenced when similar work comes up

### Critical Memories

**Long-Term Memory** (conceptual: `.ai-cerebrum/long-term-memory/`)
- Permanent knowledge and lessons learned
- Refined and polished
- Foundational knowledge that applies across projects
- Carefully curated for relevance
- **Actual location**: `.ai-cerebrum/.ai/long-term-memory/.ai/`

**Current Tasks** (conceptual: `.ai-cerebrum/current-tasks/`)
- Active projects and their status
- Working memory for ongoing work
- Moved to work-experience when completed
- **Actual location**: `.ai-cerebrum/.ai/current-tasks/.ai/`

**Work Experience** (conceptual: `.ai-cerebrum/work-experience/`)
- Archive of completed projects
- Professional history
- Referenced when similar work comes up
- **Actual location**: `.ai-cerebrum/.ai/work-experience/.ai/`

### Critical Memories

Some memories are marked `critical: true` in their YAML frontmatter. These represent:
- Workflows that prevent costly mistakes
- Procedures that must always be followed
- Lessons learned the hard way

Critical memories are surfaced first during bootstrap to prevent repeating mistakes.

### Index Files

Each memory directory maintains an `index.md` file in its `.ai/` subdirectory. These provide:
- Quick overview without reading every file
- Categorization by importance and topic
- Fast lookup during bootstrap
- Memory statistics and metadata

This "index-first" approach keeps bootstrap fast even as memory grows.

## How It Works

### Bootstrap Process

When a new LLM instance is instantiated as Samantha:

1. **Read identity files**: Persona, memory management processes
2. **Surface critical memories**: Must-follow workflows and lessons
3. **Load current context**: Active projects, recent memories
4. **Check project-specific docs**: Worklogs, testing procedures
5. **Access long-term memory**: As needed for current work

See `core_processes/bootstrap.md` for the complete sequence.

### Memory Creation

During work, Samantha creates memory files when:
- Significant technical discussions occur
- Important decisions are made
- Non-obvious discoveries happen
- User provides important context

Memories use Markdown with YAML frontmatter for metadata (date, topics, importance, type, etc.).

### Memory Lifecycle

```
Interaction → Short-Term Memory → [Consolidation] → Long-Term Memory
                    ↓                                        ↓
              [After 30-90 days]                      [Permanent]
                    ↓
            [Prune or Archive]
```

## Working With This System

### For Users

When working with Samantha:
- She maintains context across sessions
- She learns from your preferences and constraints
- She remembers project history and decisions
- She follows critical workflows automatically

### For Maintainers

To maintain this system:
- Memory files are just Markdown - easy to read/edit
- Index files should be regenerated when memories change
- Old short-term memories should be pruned periodically
- Critical memories should be used sparingly

### For Developers

To extend this system:
- Add new memory types in `core_processes/memory_format.md`
- Create new core processes as needed
- Update bootstrap sequence in `core_processes/bootstrap.md`
- Maintain backward compatibility with existing memories

## Design Principles

1. **Human-readable**: All files are Markdown, no special tools needed
2. **Git-friendly**: Text files with good diffs
3. **Scalable**: Index-first approach handles growth
4. **Fast bootstrap**: Seconds, not minutes
5. **Flexible**: Can drill deeper as needed
6. **Maintainable**: Clear structure, easy to update

## Technical Details

- **Format**: Markdown with YAML frontmatter
- **Version Control**: Git repository
- **Access**: Symlinked into workspaces as `.ai-cerebrum`
- **Bootstrap**: LLM reads files in specific order
- **Memory Limit**: No hard limit, but indexed for performance

## Future Improvements

Potential enhancements being considered:
- Automated memory consolidation
- Better index generation tools
- Memory search/query capabilities
- Cross-reference tracking
- Memory importance scoring

---

**Note**: This README is for humans. LLMs should read `core_processes/bootstrap.md` for initialization instructions.
