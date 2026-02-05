# Samantha-LLM Command Reference

Complete reference for all `samantha-llm` commands.

## Table of Contents

- [Installation & Setup](#installation--setup)
- [Agent Configuration](#agent-configuration)
- [Workspace Management](#workspace-management)
- [Memory Search (QMD)](#memory-search-qmd)
- [Help & Information](#help--information)

---

## Installation & Setup

### install

Install samantha-llm system-wide.

```bash
./samantha-llm install
```

Creates:
- Config directory: `~/.config/samantha-llm/`
- System-wide command in PATH
- Platform-specific installation:
  - **Linux/macOS**: Symlink in `~/.local/bin/`
  - **Windows**: Copy + .bat wrapper in `%LOCALAPPDATA%\Programs\samantha-llm\`

### uninstall

Remove samantha-llm installation.

```bash
samantha-llm uninstall
```

Removes:
- System command
- Config directory (with confirmation)

### status

Show installation status and configuration.

```bash
samantha-llm status
```

Displays:
- Installation status
- Config file location
- Repository location
- Configured agents
- Default agent

---

## Agent Configuration

### setup

Configure an agent for LLM sessions (interactive).

```bash
samantha-llm setup
```

Prompts for:
- Agent name (e.g., "claude", "copilot")
- Command to run agent
- Optional bootstrap file

**Set default agent:**
```bash
samantha-llm setup --default AGENT
```

Supported agents:
- **Claude Code** - Anthropic's official CLI
- **GitHub Copilot** - Microsoft's AI pair programmer
- **Abacus.ai** - Abacus platform CLI
- **Custom** - Any command that accepts text input

### agents

List all configured agents.

```bash
samantha-llm agents
```

Shows:
- Agent names
- Commands
- Default agent (marked with ★)

---

## Workspace Management

### link

Link current directory to samantha-llm (creates `.ai-cerebrum` symlink).

```bash
cd /path/to/project
samantha-llm link
```

Creates: `.ai-cerebrum` → `/path/to/samantha-llm`

This gives the LLM access to:
- Bootstrap instructions
- Memory system
- Core processes

### unlink

Remove `.ai-cerebrum` symlink from current directory.

```bash
samantha-llm unlink
```

### start

Start a Samantha Hartwell session.

```bash
samantha-llm start [AGENT]
```

**With default agent:**
```bash
samantha-llm start
```

**With specific agent:**
```bash
samantha-llm start claude
```

**What it does:**
1. Auto-links workspace (if not already linked)
2. Runs agent with bootstrap prompt
3. Cleans up auto-link when session ends

**Manual linking preserved:**
- If you manually ran `samantha-llm link`, the symlink persists
- If auto-linked by `start`, symlink removed on exit

---

## Memory Search (QMD)

Semantic search across Samantha's memories using [qmd](https://github.com/tobi/qmd).

### qmd install

Install qmd memory search engine and dependencies.

```bash
samantha-llm qmd install
```

**What it installs:**
1. **Bun runtime** (~10MB) - JavaScript runtime for qmd
2. **qmd** (~5MB) - Memory search CLI
3. **AI models** (~2GB) - Downloaded on first use
   - Embedding model (300MB)
   - Re-ranking model (640MB)
   - Query expansion model (1.1GB)

**Models cached in:** `~/.cache/qmd/models/`

**Supported platforms:**
- Linux (all distros)
- macOS (Intel and Apple Silicon)
- Windows (via WSL)

### qmd install-bun

Install only Bun runtime (if you want to install qmd separately).

```bash
samantha-llm qmd install-bun
```

### qmd status

Show qmd installation status.

```bash
samantha-llm qmd status
```

Shows:
- Bun installation and version
- qmd installation and version
- Model download status
- Config file location

### qmd check

Quick check if qmd is available (exit code 0 = installed, 1 = not installed).

```bash
samantha-llm qmd check && echo "Ready!"
```

Useful in scripts.

---

### memories index

Index cerebrum files for semantic search.

```bash
samantha-llm memories index
```

**What it indexes:**
- `.ai/short-term-memory/.ai/` - Recent memories
- `.ai/long-term-memory/.ai/` - Permanent knowledge
- `.ai/current-tasks/.ai/` - Active projects
- `.ai/work-experience/.ai/` - Completed work

**Creates:** `samantha-cerebrum` collection in qmd

**Run after:**
- Installing qmd
- Creating new memories
- Updating existing memories

**Incremental:** Only changed files re-indexed

### memories search

Search memories semantically.

```bash
samantha-llm memories search <query>
```

**Examples:**
```bash
# Search for testing workflows
samantha-llm memories search "testing workflows"

# Search for API design patterns
samantha-llm memories search "API design patterns"

# Search for project setup
samantha-llm memories search "how to set up new project"
```

**Search modes:**
- **Hybrid** (default) - Keyword + semantic + AI re-ranking
  - Best results, most accurate
  - Uses all three qmd models

- **Keyword** (fast) - BM25 full-text search
  - Use qmd directly: `qmd search samantha-cerebrum "query"`

- **Semantic** (vector) - Embedding similarity
  - Use qmd directly: `qmd vsearch samantha-cerebrum "query"`

**Output format:**
- Markdown (default) - Human-readable with context
- JSON - Machine-parseable: `qmd query samantha-cerebrum "query" --json`
- Plain text - Simple: `qmd query samantha-cerebrum "query" --text`

**Result limit:**
- Default: 10 results
- Custom: `qmd query samantha-cerebrum "query" --limit 20`

---

## Help & Information

### help

Show command reference.

```bash
samantha-llm help
```

### version

Show version and platform information.

```bash
samantha-llm version
```

---

## LLM Integration

The LLM can use these commands via the Bash tool:

```python
# Search memories
Bash("samantha-llm memories search 'critical workflows'")

# Check qmd status
Bash("samantha-llm qmd status")

# Index new memories
Bash("samantha-llm memories index")
```

No special integration needed - works like any CLI tool (git, grep, etc.)

---

## Configuration Files

**Main config:** `~/.config/samantha-llm/config.json`
```json
{
  "repo_path": "/path/to/samantha-llm",
  "default_agent": "claude",
  "agents": {
    "claude": {
      "command": "claude --dangerously-add-system-prompt",
      "bootstrap_file": "BOOTSTRAP_PROMPT.md"
    }
  },
  "workspaces": {}
}
```

**QMD config:** `~/.config/samantha-llm/qmd-config.json`
```json
{
  "enabled": true,
  "auto_index": true,
  "search_mode": "hybrid",
  "models_path": "~/.cache/qmd/models"
}
```

---

## Troubleshooting

### qmd not found after install

**Restart your shell:**
```bash
source ~/.bashrc  # or ~/.zshrc
```

**Or add Bun to PATH manually:**
```bash
export PATH="$HOME/.bun/bin:$PATH"
```

### Models downloading slowly

Models are large (~2GB total). First search will be slow while they download. Subsequent searches are fast (models cached).

### Collection not found

Run indexing first:
```bash
samantha-llm memories index
```

### No results found

- Try broader query terms
- Use hybrid search (default) for best results
- Verify files indexed: `qmd list samantha-cerebrum`

---

## Advanced Usage

### Direct qmd Usage

For advanced options, use qmd directly:

```bash
# List collections
qmd list

# Detailed search with options
qmd query samantha-cerebrum "performance optimization" \
  --limit 5 \
  --json

# Keyword-only search
qmd search samantha-cerebrum "testing"

# Vector-only search
qmd vsearch samantha-cerebrum "API design"

# Get specific document
qmd get samantha-cerebrum <docid>
```

### Custom Search Scripts

```bash
#!/bin/bash
# search-critical.sh - Find critical memories

samantha-llm memories search "critical: true" | \
  grep -A 5 "importance: high"
```

---

## See Also

- [README.md](README.md) - Getting started guide
- [qmd documentation](https://github.com/tobi/qmd) - qmd project
- [Bun documentation](https://bun.sh/docs) - Bun runtime
