# Compressed Index Format Specification

## Overview

This document defines the compressed JSON format for cerebrum index files. The compressed format reduces token consumption during bootstrap while maintaining all essential information.

## Design Goals

1. **Token Efficiency**: 60-70% reduction in tokens compared to markdown
2. **Information Preservation**: No loss of critical data
3. **Machine Readable**: Easy for LLMs to parse and process
4. **Human Maintainable**: Generated from human-readable markdown source

## Format Specification

### Root Object

```json
{
  "version": "1.0",
  "last_updated": "YYYY-MM-DD",
  "metadata": { ... },
  "critical_memories": [ ... ],
  "high_priority": [ ... ],
  "recent_high_importance": [ ... ],
  "recent_medium_importance": [ ... ]
}
```

### Metadata Object

```json
{
  "total_memories": <number>,
  "critical_count": <number>,
  "high_importance": <number>,
  "medium_importance": <number>
}
```

### Memory Object (Critical)

Critical memories include a `rule` field for quick reference:

```json
{
  "id": "YYYY-MM-DD_filename_without_extension",
  "date": "YYYY-MM-DD",
  "title": "Brief Title",
  "rule": "One-sentence critical rule or workflow",
  "importance": "high|medium|low",
  "type": "quick-reference|decision|technical|interaction|learning",
  "references": <number>,
  "topics": ["tag1", "tag2"],
  "project": "project-name" // optional
}
```

### Memory Object (Standard)

Standard memories include a `summary` field:

```json
{
  "id": "YYYY-MM-DD_filename_without_extension",
  "date": "YYYY-MM-DD",
  "title": "Brief Title",
  "summary": "1-2 sentence summary of the memory",
  "importance": "high|medium|low",
  "type": "quick-reference|decision|technical|interaction|learning",
  "references": <number>,
  "topics": ["tag1", "tag2"],
  "project": "project-name" // optional
}
```

## Token Savings Analysis

### Markdown Format (Original)

```markdown
#### 2025-11-21: Bootstrap Compression Research and Strategy
**Topics**: cerebrum, bootstrap, compression, optimization, ai-memory, research
**Type**: learning
**Project**: cerebrum-optimization
**Summary**: Comprehensive research into AI memory compression techniques...
**File**: `2025-11-21_bootstrap_compression_research.md`
**References**: 0
```

**Estimated tokens**: ~150-200 tokens (with formatting, markdown syntax, labels)

### JSON Format (Compressed)

```json
{
  "id": "2025-11-21_bootstrap_compression_research",
  "date": "2025-11-21",
  "title": "Bootstrap Compression Research and Strategy",
  "summary": "Comprehensive research into AI memory compression techniques...",
  "importance": "high",
  "type": "learning",
  "references": 0,
  "topics": ["cerebrum", "bootstrap", "compression", "optimization", "ai-memory", "research"],
  "project": "cerebrum-optimization"
}
```

**Estimated tokens**: ~60-80 tokens (structured, no formatting overhead)

**Savings**: 60-70% reduction per memory entry

## Usage in Bootstrap

### Loading Compressed Index

```javascript
// Read compressed index
const index = JSON.parse(fs.readFileSync('.ai-cerebrum/short-term-memory/.ai/index.compact.json'));

// Access critical memories
for (const memory of index.critical_memories) {
  console.log(`CRITICAL: ${memory.rule}`);
  // Optionally load full memory file if needed
}

// Access recent high-importance memories
for (const memory of index.recent_high_importance) {
  console.log(`${memory.title}: ${memory.summary}`);
}
```

### Fallback to Full Memory

If more detail is needed, load the full markdown file:

```javascript
const fullMemory = fs.readFileSync(
  `.ai-cerebrum/short-term-memory/.ai/${memory.id}.md`
);
```

## Generation Process

The compressed index should be generated automatically from the markdown source:

1. Parse markdown index file
2. Extract memory entries with metadata
3. Convert to JSON structure
4. Write to `.compact.json` file

**Source of Truth**: Markdown files remain the source of truth
**Build Artifact**: JSON files are generated artifacts

## Maintenance

- Update markdown index as usual
- Regenerate compressed JSON after changes
- Version both formats in git for transparency
- Document any schema changes in this file

## Future Enhancements

1. **Binary Format**: Further compression using MessagePack or Protocol Buffers
2. **Embedding Vectors**: Include pre-computed embeddings for semantic search
3. **Compression Levels**: Multiple compression levels (minimal, standard, full)
4. **Incremental Updates**: Only regenerate changed sections

## Related Files

- Markdown source: `.ai-cerebrum/short-term-memory/.ai/index.md`
- Compressed JSON: `.ai-cerebrum/short-term-memory/.ai/index.compact.json`
- Bootstrap process: `.ai-cerebrum/core_processes/bootstrap.md`
- This specification: `.ai-cerebrum/core_processes/compressed_index_format.md`
