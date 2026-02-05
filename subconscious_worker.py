#!/usr/bin/env python3
"""
Subconscious worker - processes session transcripts asynchronously.

This script runs as a detached background process after a session ends.
It analyzes the transcript, updates memories, and generates guidance.

Usage:
    python subconscious_worker.py <transcript_file> <cerebrum_path>
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

# Import session workspace management
try:
    from session_workspace import SessionWorkspace
    HAS_WORKSPACE = True
except ImportError:
    HAS_WORKSPACE = False

# Import terminal parser if available
try:
    import importlib.util
    parser_path = Path(__file__).parent / 'terminal_parser.py'
    if parser_path.exists():
        spec = importlib.util.spec_from_file_location("terminal_parser", parser_path)
        terminal_parser = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(terminal_parser)
        HAS_PARSER = True
    else:
        HAS_PARSER = False
except Exception:
    HAS_PARSER = False

# Import conversation analyzer if available
try:
    analyzer_path = Path(__file__).parent / 'claude_analyzer.py'
    if analyzer_path.exists():
        spec = importlib.util.spec_from_file_location("claude_analyzer", analyzer_path)
        claude_analyzer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(claude_analyzer)
        HAS_ANALYZER = True
    else:
        HAS_ANALYZER = False
except Exception:
    HAS_ANALYZER = False

# Import conversation chunker if available
try:
    chunker_path = Path(__file__).parent / 'conversation_chunker.py'
    if chunker_path.exists():
        spec = importlib.util.spec_from_file_location("conversation_chunker", chunker_path)
        conversation_chunker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(conversation_chunker)
        HAS_CHUNKER = True
    else:
        HAS_CHUNKER = False
except Exception:
    HAS_CHUNKER = False


def log(log_file: Path, message: str):
    """Write to processing log."""
    with open(log_file, 'a') as f:
        timestamp = datetime.now().isoformat()
        f.write(f"{timestamp} {message}\n")
        f.flush()


def load_transcript(filepath: Path) -> list:
    """Load JSONL transcript file."""
    events = []
    with open(filepath) as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
    return events


def find_terminal_recording(transcript_file: Path, cerebrum_path: Path) -> Optional[Path]:
    """
    Find terminal recording file matching transcript session ID.

    Args:
        transcript_file: Path to transcript JSONL file
        cerebrum_path: Path to cerebrum root

    Returns:
        Path to terminal recording if found, None otherwise
    """
    # Extract session ID from transcript filename
    # Format: transcript_YYYYMMDD_HHMMSS_*.jsonl -> terminal_YYYYMMDD_HHMMSS.txt
    import re
    match = re.search(r'transcript_(\d{8}_\d{6})', transcript_file.name)
    if not match:
        return None

    session_id = match.group(1)

    # Look for terminal recording
    recordings_dir = cerebrum_path / '.ai' / 'subconscious' / '.ai' / 'recordings'
    if not recordings_dir.exists():
        return None

    recording_file = recordings_dir / f'terminal_{session_id}.txt'
    if recording_file.exists():
        return recording_file

    return None


def process_transcript_basic(events: list, terminal_data: Optional[dict] = None) -> dict:
    """
    Basic transcript processing (placeholder for LLM processing).

    In Phase 3, this will call an LLM to analyze the transcript.
    For now, just extract simple statistics.

    Args:
        events: List of transcript events
        terminal_data: Optional parsed terminal recording data

    Returns:
        Analysis dictionary
    """
    session_start = next((e for e in events if e['type'] == 'session_start'), None)
    session_end = next((e for e in events if e['type'] == 'session_end'), None)

    analysis = {
        'event_count': len(events),
        'agent': session_start['metadata']['agent'] if session_start else 'unknown',
        'workspace': session_start['metadata']['workspace'] if session_start else 'unknown',
        'duration': session_end['metadata']['duration'] if session_end else 0,
        'session_id': session_start['metadata']['session_id'] if session_start else 'unknown'
    }

    # Add terminal recording data if available
    if terminal_data:
        analysis['has_terminal_recording'] = True
        analysis['terminal_text_length'] = len(terminal_data.get('raw_text', ''))
        analysis['terminal_messages'] = len(terminal_data.get('messages', []))

        # Include session metadata from terminal recording
        if 'metadata' in terminal_data:
            analysis['terminal_metadata'] = terminal_data['metadata']
    else:
        analysis['has_terminal_recording'] = False

    return analysis


def _analyze_with_chunking(
    conversation_text: str,
    session_id: str,
    prompt_path: Path,
    analyses_dir: Path,
    parsed_dir: Path,
    log_func,
    workspace: Optional['SessionWorkspace'] = None
):
    """
    Analyze long conversation using chunking with context passing.

    Args:
        conversation_text: Full conversation text
        session_id: Session identifier
        prompt_path: Path to analysis prompt
        analyses_dir: Directory for raw LLM output
        parsed_dir: Directory for parsed text
        log_func: Logging function to call
        workspace: Optional SessionWorkspace for manifest tracking

    Returns:
        Combined AnalysisResult from all chunks
    """
    # Create chunker
    chunker = conversation_chunker.create_chunker(target_size=150000)
    chunks = chunker.chunk(conversation_text, strategy='natural')

    log_func(f"[LLM] Split conversation into {len(chunks)} chunks")

    # Initialize chunk manifest if workspace provided
    if workspace:
        workspace.init_chunk_manifest(len(chunks))

    # Create analyzer with output_dir to save raw LLM output for each chunk
    analyzer = claude_analyzer.create_analyzer(prompt_path, output_dir=analyses_dir)

    # Process each chunk with context from previous chunks
    chunk_results = []
    accumulated_context = ""

    for chunk in chunks:
        chunk_num = chunk.chunk_index + 1
        log_func(f"[LLM] Analyzing chunk {chunk_num}/{chunk.total_chunks} ({len(chunk):,} chars, boundary: {chunk.boundary_reason})")

        # Update chunk status to processing
        if workspace:
            workspace.update_chunk_status(chunk_num, 'processing', {
                'started_at': datetime.now().isoformat()
            })

        # Prepend context from previous chunks (if any)
        if accumulated_context:
            chunk_text_with_context = f"{accumulated_context}\n\n---\n\n{chunk.text}"
        else:
            chunk_text_with_context = chunk.text

        # Write chunk to temp file
        chunk_file = parsed_dir / f'parsed_{session_id}_chunk{chunk_num}.txt'
        chunk_file.write_text(chunk_text_with_context)

        # Analyze chunk (raw output automatically saved to analyses_dir)
        try:
            result = analyzer.analyze(chunk_file)

            log_func(f"[LLM] Chunk {chunk_num} complete: {len(result.patterns)} patterns, {len(result.decisions)} decisions")
            log_func(f"[LLM] Raw output saved: analysis_{session_id}_chunk{chunk_num}.md")

            chunk_results.append(result)

            # Mark chunk as complete
            if workspace:
                workspace.update_chunk_status(chunk_num, 'complete', {
                    'completed_at': datetime.now().isoformat(),
                    'patterns_count': len(result.patterns),
                    'decisions_count': len(result.decisions)
                })

            # Update accumulated context for next chunk
            if chunk_num < chunk.total_chunks:
                accumulated_context = result.to_context_summary()

        except Exception as e:
            log_func(f"[ERROR] Chunk {chunk_num} analysis failed: {e}")

            # Mark chunk as failed
            if workspace:
                workspace.update_chunk_status(chunk_num, 'failed', {
                    'failed_at': datetime.now().isoformat(),
                    'error': str(e),
                    'attempts': workspace.get_chunk_manifest()['chunks'][str(chunk_num)].get('attempts', 0) + 1
                })

            # Continue with remaining chunks
            continue

    # Merge all chunk results
    log_func(f"[LLM] Merging {len(chunk_results)} chunk results...")
    merged_result = _merge_chunk_results(chunk_results, session_id, log_func)

    # Save combined parsed analysis (Part 2 only - for guidance)
    combined_parsed_file = analyses_dir / f'analysis_{session_id}_parsed.md'
    combined_parsed_file.write_text(merged_result.to_markdown())
    log_func(f"[LLM] Combined parsed analysis saved to: {combined_parsed_file}")

    # Combine all raw chunk outputs (includes Part 1 + Part 2 for each chunk)
    log_func(f"[LLM] Combining raw chunk outputs...")
    combined_sections = []
    for i in range(len(chunk_results)):
        chunk_num = i + 1
        chunk_raw_file = analyses_dir / f'analysis_{session_id}_chunk{chunk_num}.md'
        if chunk_raw_file.exists():
            chunk_content = chunk_raw_file.read_text()
            combined_sections.append(f"# Chunk {chunk_num}/{len(chunk_results)}\n\n{chunk_content}")

    # Save combined raw output (full detailed analysis)
    combined_raw_file = analyses_dir / f'analysis_{session_id}_full.md'
    combined_raw_file.write_text("\n\n---\n\n".join(combined_sections))
    log_func(f"[LLM] Combined raw analysis saved to: {combined_raw_file}")

    return merged_result


def _merge_chunk_results(chunk_results, session_id: str, log_func):
    """
    Merge multiple AnalysisResult objects into one.

    Args:
        chunk_results: List of AnalysisResult objects
        session_id: Session identifier
        log_func: Logging function to call

    Returns:
        Combined AnalysisResult
    """
    from conversation_analyzer import AnalysisResult

    if not chunk_results:
        return AnalysisResult()

    if len(chunk_results) == 1:
        return chunk_results[0]

    # Combine all lists, removing duplicates while preserving order
    def dedupe_list(items):
        seen = set()
        result = []
        for item in items:
            # Normalize for comparison (lowercase, strip)
            normalized = item.lower().strip()
            if normalized not in seen:
                seen.add(normalized)
                result.append(item)
        return result

    all_patterns = []
    all_decisions = []
    all_todos = []
    all_preferences = []
    all_learnings = []
    summaries = []

    for i, result in enumerate(chunk_results):
        # Add chunk marker to items for traceability
        chunk_num = i + 1

        all_patterns.extend(result.patterns)
        all_decisions.extend(result.decisions)
        all_todos.extend(result.todos)
        all_preferences.extend(result.preferences)
        all_learnings.extend(result.learnings)

        # Extract session summary (truncate if too long to keep guidance lightweight)
        if result.summary:
            summary_text = result.summary.strip()
            # If summary is very long (>500 chars), it likely includes Part 1 content - truncate it
            if len(summary_text) > 500:
                summary_text = summary_text[:497] + "..."
            summaries.append(f"**Chunk {chunk_num}**: {summary_text}")

    # Deduplicate
    merged = AnalysisResult(
        patterns=dedupe_list(all_patterns),
        decisions=dedupe_list(all_decisions),
        todos=dedupe_list(all_todos),
        preferences=dedupe_list(all_preferences),
        learnings=dedupe_list(all_learnings),
        summary="\n\n".join(summaries) if summaries else None
    )

    log_func(f"[LLM] Merged results: {len(merged.patterns)} patterns, {len(merged.decisions)} decisions, {len(merged.todos)} TODOs")

    return merged


def process_transcript_llm(terminal_data: dict, cerebrum_path: Path, log_func, workspace: Optional['SessionWorkspace'] = None) -> Optional[dict]:
    """
    Process transcript using LLM analysis.

    Args:
        terminal_data: Parsed terminal recording data
        cerebrum_path: Path to cerebrum root
        log_func: Logging function to call
        workspace: Optional SessionWorkspace for session-isolated processing

    Returns:
        Analysis result dict if successful, None otherwise
    """
    if not HAS_ANALYZER:
        log_func("[WARN] LLM analyzer not available, using basic processing")
        return None

    try:
        # Find the prompt file
        prompt_path = cerebrum_path / '.ai' / 'subconscious' / '.ai' / 'prompts' / 'analysis-prompt-v2.txt'
        if not prompt_path.exists():
            log_func(f"[WARN] Analysis prompt not found: {prompt_path}")
            return None

        # Use workspace directories if available, otherwise fall back to old paths
        if workspace:
            parsed_dir = workspace.parsed_dir
            analyses_dir = workspace.analyses_dir
        else:
            recordings_dir = cerebrum_path / '.ai' / 'subconscious' / '.ai' / 'recordings'
            parsed_dir = recordings_dir.parent / 'parsed'
            parsed_dir.mkdir(exist_ok=True)
            analyses_dir = recordings_dir.parent / 'analyses'
            analyses_dir.mkdir(exist_ok=True)

        # Get conversation text
        session_id = terminal_data.get('metadata', {}).get('session_id', 'unknown')
        conversation_text = terminal_data['raw_text']
        text_size = len(conversation_text)

        log_func(f"[LLM] Conversation size: {text_size:,} characters")

        # Check if chunking is needed
        CHUNK_THRESHOLD = 150000  # ~200K tokens with prompt
        needs_chunking = text_size > CHUNK_THRESHOLD and HAS_CHUNKER

        if needs_chunking:
            log_func(f"[LLM] Conversation exceeds {CHUNK_THRESHOLD:,} chars, using chunked analysis")
            result = _analyze_with_chunking(
                conversation_text,
                session_id,
                prompt_path,
                analyses_dir,
                parsed_dir,
                log_func,
                workspace
            )
        else:
            # Single-pass analysis (original behavior)
            log_func(f"[LLM] Starting conversation analysis...")

            # Write to parsed directory
            parsed_file = parsed_dir / f'parsed_{session_id}.txt'
            parsed_file.write_text(conversation_text)

            # Create analyzer and run analysis
            analyzer = claude_analyzer.create_analyzer(prompt_path, output_dir=analyses_dir)
            result = analyzer.analyze(parsed_file)

            log_func(f"[LLM] Analysis complete: {len(result.patterns)} patterns, {len(result.decisions)} decisions, {len(result.todos)} TODOs")
            log_func(f"[LLM] Raw output saved to: {analyses_dir / f'analysis_{session_id}.md'}")

        # Convert to dict for easier handling
        analysis_dict = {
            'patterns': result.patterns,
            'decisions': result.decisions,
            'todos': result.todos,
            'preferences': result.preferences,
            'learnings': result.learnings,
            'summary': result.summary,
            'llm_analysis': True
        }

        return analysis_dict

    except Exception as e:
        log_func(f"[ERROR] LLM analysis failed: {e}")
        import traceback
        log_func(f"[ERROR] {traceback.format_exc()}")
        return None


def finalize_session_memories(session_workspace: 'SessionWorkspace', cerebrum_path: Path, log_func) -> list:
    """
    Finalize session by moving memories to cerebrum and updating index.

    Args:
        session_workspace: SessionWorkspace instance
        cerebrum_path: Path to cerebrum root
        log_func: Logging function

    Returns:
        List of finalized memory file paths
    """
    import json
    import shutil

    # Find all memory files in session workspace
    memories_dir = session_workspace.memories_dir
    if not memories_dir.exists():
        log_func("[FINALIZE] No memories directory in session workspace")
        return []

    memory_files = list(memories_dir.glob('*.md'))
    if not memory_files:
        log_func("[FINALIZE] No memory files to finalize")
        return []

    log_func(f"[FINALIZE] Found {len(memory_files)} memory files to finalize")

    # Target directories
    cerebrum_memories_dir = cerebrum_path / '.ai' / 'short-term-memory' / '.ai'
    cerebrum_memories_dir.mkdir(parents=True, exist_ok=True)

    index_file = cerebrum_memories_dir / 'index.json'

    # Load current index
    if index_file.exists():
        with open(index_file) as f:
            index = json.load(f)
    else:
        # Create new index structure
        index = {
            'last_updated': '',
            'total_memories': 0,
            'critical': [],
            'high_priority': [],
            'recent': {
                'high_importance': [],
                'medium_importance': []
            },
            'stats': {
                'by_importance': {'high': 0, 'medium': 0, 'low': 0},
                'by_type': {},
                'by_project': {}
            }
        }

    finalized = []

    for memory_file in memory_files:
        # Parse frontmatter to get metadata
        content = memory_file.read_text()

        # Extract YAML frontmatter
        if content.startswith('---\n'):
            parts = content.split('---\n', 2)
            if len(parts) >= 3:
                # Simple YAML parsing (avoid external dependency)
                frontmatter = {}
                for line in parts[1].split('\n'):
                    line = line.strip()
                    if ': ' in line:
                        key, value = line.split(': ', 1)
                        # Handle lists
                        if value.startswith('[') and value.endswith(']'):
                            value = [v.strip() for v in value.strip('[]').split(',')]
                        # Handle numbers
                        elif value.isdigit():
                            value = int(value)
                        frontmatter[key] = value
            else:
                frontmatter = {}
        else:
            frontmatter = {}

        # Copy memory to cerebrum
        dest_file = cerebrum_memories_dir / memory_file.name
        shutil.copy2(memory_file, dest_file)
        log_func(f"[FINALIZE] Copied {memory_file.name} to cerebrum")
        finalized.append(dest_file)

        # Update index
        date = frontmatter.get('date', '')
        topics = frontmatter.get('topics', [])
        if isinstance(topics, str):
            topics = [t.strip() for t in topics.strip('[]').split(',')]

        importance = frontmatter.get('importance', 'medium')
        mem_type = frontmatter.get('type', 'session-analysis')
        project = frontmatter.get('project', '')

        # Create index entry
        entry = {
            'date': date,
            'title': memory_file.stem.replace('_', ' ').title(),
            'topics': topics,
            'type': mem_type,
            'project': project,
            'summary': f"Auto-generated from session {session_workspace.session_id}",
            'file': memory_file.name,
            'references': 0
        }

        # Add to appropriate section
        if importance == 'high':
            index['recent']['high_importance'].insert(0, entry)
        else:
            index['recent']['medium_importance'].insert(0, entry)

        # Update stats
        index['stats']['by_importance'][importance] = index['stats']['by_importance'].get(importance, 0) + 1
        index['stats']['by_type'][mem_type] = index['stats']['by_type'].get(mem_type, 0) + 1
        if project:
            index['stats']['by_project'][project] = index['stats']['by_project'].get(project, 0) + 1

    # Update index metadata
    from datetime import datetime
    index['last_updated'] = datetime.now().strftime('%Y-%m-%d')
    index['total_memories'] = index.get('total_memories', 0) + len(finalized)

    # Write updated index
    with open(index_file, 'w') as f:
        json.dump(index, f, indent=2)

    log_func(f"[FINALIZE] Updated index.json with {len(finalized)} new memories")

    return finalized


def generate_guidance_basic(cerebrum_path: Path, analysis: dict, llm_analysis: Optional[dict] = None, workspace: Optional['SessionWorkspace'] = None):
    """
    Generate lightweight guidance file - just a session log for quick orientation.

    Args:
        cerebrum_path: Path to cerebrum root
        analysis: Basic session analysis
        llm_analysis: Optional LLM analysis results
        workspace: Optional SessionWorkspace (writes to session-specific location if provided)
    """
    # Write to session workspace if available, otherwise use global guidance
    if workspace:
        guidance_file = workspace.guidance_file
    else:
        guidance_dir = cerebrum_path / '.ai' / 'subconscious' / '.ai'
        guidance_dir.mkdir(parents=True, exist_ok=True)
        guidance_file = guidance_dir / 'guidance.md'

    # Extract date from session_id or use current date
    session_id = analysis.get('session_id', 'unknown')
    session_date = session_id.split('_')[0] if '_' in session_id else datetime.now().strftime('%Y%m%d')

    # Format: YYYYMMDD -> YYYY-MM-DD
    if len(session_date) == 8:
        formatted_date = f"{session_date[0:4]}-{session_date[4:6]}-{session_date[6:8]}"
    else:
        formatted_date = datetime.now().strftime('%Y-%m-%d')

    # Build lightweight session entry
    content_parts = [
        f"""---
last_updated: {datetime.now().isoformat()}
---

# Subconscious Guidance

Quick orientation from recent sessions. For detailed analysis, see files in `.ai/subconscious/.ai/analyses/`.

## Recent Sessions
"""
    ]

    # Create session entry
    duration_min = int(analysis['duration'] / 60)
    workspace = analysis.get('workspace', 'unknown')

    # Create content summary from LLM analysis
    if llm_analysis and not llm_analysis.get('empty', False):
        summary = llm_analysis.get('summary', '')

        # Extract meaningful content from summary (skip headings, chunk markers)
        if summary:
            summary_lines = []
            for line in summary.split('\n'):
                line = line.strip()
                # Skip empty lines, chunk markers, markdown headings, and labels
                if (line and
                    not line.startswith('**Chunk') and
                    not line.startswith('#') and
                    not line.endswith(':') and
                    not line.startswith('**Detailed') and
                    not line.startswith('**High-Level')):
                    summary_lines.append(line)

            # Take first 2-3 meaningful lines or bullet points
            if summary_lines:
                summary_text = ' '.join(summary_lines[:2])
                # Truncate if too long
                if len(summary_text) > 200:
                    summary_text = summary_text[:200] + "..."
            else:
                summary_text = 'Session analyzed'
        else:
            summary_text = 'Session analyzed'

        # Link to detailed analysis
        analysis_link = f"analysis_{session_id}_full.md" if session_id != 'unknown' else "analysis files"

        session_entry = f"- **{formatted_date}** ({duration_min}min, {workspace}): {summary_text} [[{analysis_link}]]"
    else:
        session_entry = f"- **{formatted_date}** ({duration_min}min, {workspace}): Processing... (analysis pending)"

    content_parts.append(session_entry)
    content_parts.append("")

    content_parts.append("""
---

*Guidance is lightweight - detailed session notes and memories are in analysis files and will be processed into cerebrum memories in Phase 4.*
""")

    guidance_content = "\n".join(content_parts)
    guidance_file.write_text(guidance_content)
    return guidance_file


def main():
    """Main worker process."""
    if len(sys.argv) < 3:
        print("Usage: python subconscious_worker.py <transcript_file> <cerebrum_path>")
        sys.exit(1)

    transcript_file = Path(sys.argv[1])
    cerebrum_path = Path(sys.argv[2])

    # Extract session ID from transcript filename
    import re
    match = re.search(r'transcript_(\d{8}_\d{6})', transcript_file.name)
    session_id = match.group(1) if match else 'unknown'

    # Create session workspace if available
    workspace = None
    if HAS_WORKSPACE and session_id != 'unknown':
        workspace = SessionWorkspace(session_id, cerebrum_path)
        workspace.create()
        log_func = workspace.log
        log_file = workspace.log_file
    else:
        # Fall back to old global logging
        log_dir = cerebrum_path / '.ai' / 'subconscious' / '.ai'
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / 'processing.log'
        log_func = lambda msg: log(log_file, msg)

    # Create lock file (global for now, per-session later)
    lockfile = (workspace.root if workspace else log_dir) / '.processing.lock'

    try:
        # Acquire lock
        lockfile.touch()
        log_func(f"[START] Processing {transcript_file.name}")

        # Load transcript
        if not transcript_file.exists():
            log_func(f"[ERROR] Transcript file not found: {transcript_file}")
            if workspace:
                workspace.mark_failed(f"Transcript file not found: {transcript_file}")
            sys.exit(1)

        events = load_transcript(transcript_file)
        log_func(f"[LOAD] Loaded {len(events)} events")

        # Find and parse terminal recording if available
        terminal_data = None
        if HAS_PARSER:
            recording_file = find_terminal_recording(transcript_file, cerebrum_path)
            if recording_file:
                try:
                    terminal_data = terminal_parser.parse_terminal_recording(recording_file)
                    log_func(f"[PARSE] Parsed terminal recording: {len(terminal_data['raw_text'])} chars, {len(terminal_data['messages'])} messages")
                except Exception as e:
                    log_func(f"[WARN] Failed to parse terminal recording: {e}")

        # Process transcript (basic statistics)
        analysis = process_transcript_basic(events, terminal_data)
        log_func(f"[ANALYZE] Session: {analysis['session_id']}, Duration: {analysis['duration']:.1f}s")
        if terminal_data:
            log_func(f"[ANALYZE] Terminal recording: {analysis['terminal_text_length']} chars")

        # Phase 3: LLM processing for pattern detection
        llm_analysis = None
        if terminal_data and HAS_ANALYZER:
            llm_analysis = process_transcript_llm(terminal_data, cerebrum_path, log_func, workspace)
            if llm_analysis:
                log_func(f"[LLM] Found {len(llm_analysis.get('patterns', []))} patterns, {len(llm_analysis.get('decisions', []))} decisions")
            else:
                log_func("[LLM] Analysis not available, falling back to basic processing")

        # Phase 4: Memory creation (if LLM analysis available)
        memory_file = None
        if llm_analysis and not llm_analysis.get('empty', False):
            try:
                from memory_generator import generate_memory_file
                from conversation_analyzer import AnalysisResult

                # Convert llm_analysis dict to AnalysisResult object
                analysis_result = AnalysisResult(
                    patterns=llm_analysis.get('patterns', []),
                    decisions=llm_analysis.get('decisions', []),
                    todos=llm_analysis.get('todos', []),
                    preferences=llm_analysis.get('preferences', []),
                    learnings=llm_analysis.get('learnings', []),
                    summary=llm_analysis.get('summary')
                )

                # Generate memory file (uses workspace if available)
                memory_file = generate_memory_file(
                    analysis=analysis_result,
                    session_id=analysis['session_id'],
                    workspace=Path(analysis.get('workspace', 'unknown')),
                    duration_seconds=int(analysis['duration']),
                    cerebrum_path=cerebrum_path,
                    session_workspace=workspace
                )
                log_func(f"[MEMORY] Created memory file: {memory_file}")
            except Exception as e:
                log_func(f"[MEMORY] Failed to create memory file: {e}")
                import traceback
                log_func(f"[MEMORY] {traceback.format_exc()}")

        # Generate guidance (with LLM insights if available)
        guidance_file = generate_guidance_basic(cerebrum_path, analysis, llm_analysis, workspace)
        log_func(f"[GUIDANCE] Generated guidance: {guidance_file}")

        # Finalize session memories (move to cerebrum, update index)
        if workspace and memory_file:
            finalized_memories = finalize_session_memories(workspace, cerebrum_path, log_func)
            if finalized_memories:
                log_func(f"[FINALIZE] Finalized {len(finalized_memories)} memories to cerebrum")

        # Move processed transcript to processed directory
        processed_dir = cerebrum_path / '.ai' / 'subconscious' / '.ai' / 'processed'
        processed_dir.mkdir(parents=True, exist_ok=True)
        processed_file = processed_dir / transcript_file.name
        transcript_file.rename(processed_file)
        log_func(f"[ARCHIVE] Moved transcript to: {processed_file}")

        # Mark session as complete
        if workspace:
            workspace.mark_complete({
                'patterns_count': len(llm_analysis.get('patterns', [])) if llm_analysis else 0,
                'decisions_count': len(llm_analysis.get('decisions', [])) if llm_analysis else 0
            })

        log_func(f"[COMPLETE] Processing complete")

    except Exception as e:
        log_func(f"[ERROR] {str(e)}")
        import traceback
        log_func(f"[ERROR] {traceback.format_exc()}")
        if workspace:
            workspace.mark_failed(str(e))
        # Don't raise - just log and exit gracefully

    finally:
        # Always remove lock
        if lockfile.exists():
            lockfile.unlink()

    sys.exit(0)


if __name__ == '__main__':
    main()
