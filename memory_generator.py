#!/usr/bin/env python3
"""
Memory file generator for subconscious system.

Transforms LLM analysis results into cerebrum memory files.
"""

from pathlib import Path
from datetime import datetime
from typing import Optional
from conversation_analyzer import AnalysisResult


def generate_memory_file(
    analysis: AnalysisResult,
    session_id: str,
    workspace: Path,
    duration_seconds: int,
    cerebrum_path: Path,
) -> Path:
    """
    Generate a memory file from analysis results.

    Args:
        analysis: Parsed analysis results (patterns, decisions, learnings, etc.)
        session_id: Session identifier (YYYYMMDD_HHMMSS format)
        workspace: Path to the workspace where session occurred
        duration_seconds: Session duration in seconds
        cerebrum_path: Path to cerebrum root

    Returns:
        Path to generated memory file
    """
    # Extract date from session_id
    if '_' in session_id:
        date_str = session_id.split('_')[0]
    else:
        date_str = datetime.now().strftime('%Y%m%d')

    # Format date: YYYYMMDD -> YYYY-MM-DD
    if len(date_str) == 8:
        formatted_date = f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}"
    else:
        formatted_date = datetime.now().strftime('%Y-%m-%d')

    # Extract topics from analysis (use first few patterns/decisions as topics)
    topics = _extract_topics(analysis)

    # Determine importance based on content richness
    importance = _assess_importance(analysis, duration_seconds)

    # Generate memory content
    content = _generate_memory_content(
        analysis=analysis,
        session_id=session_id,
        formatted_date=formatted_date,
        workspace=workspace,
        duration_seconds=duration_seconds,
        topics=topics,
        importance=importance
    )

    # Save to short-term memory
    memory_dir = cerebrum_path / '.ai' / 'short-term-memory'
    memory_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename from date and first topic
    first_topic = topics[0] if topics else 'session'
    filename = f"{formatted_date}_{first_topic.replace(' ', '_')}.md"
    memory_file = memory_dir / filename

    # Write memory file
    memory_file.write_text(content)

    return memory_file


def _extract_topics(analysis: AnalysisResult, max_topics: int = 5) -> list:
    """
    Extract key topics from analysis results.

    Args:
        analysis: Analysis results
        max_topics: Maximum number of topics to extract

    Returns:
        List of topic strings
    """
    topics = []

    # Extract from decisions (often most topical)
    for decision in analysis.decisions[:3]:
        # Extract first few words or key phrase
        words = decision.split(':')[0] if ':' in decision else decision
        words = words.strip('**').strip().lower()
        # Take first 3-4 words
        topic_words = words.split()[:3]
        topic = '_'.join(topic_words).replace(',', '').replace('.', '')
        if topic and len(topic) < 30:
            topics.append(topic)

    # If not enough from decisions, add from patterns
    if len(topics) < 2 and analysis.patterns:
        for pattern in analysis.patterns[:2]:
            words = pattern.split()[0:3]
            topic = '_'.join(words).lower().replace(',', '').replace('.', '')
            if topic and len(topic) < 30 and topic not in topics:
                topics.append(topic)

    # Default topic if none found
    if not topics:
        topics = ['session_analysis']

    return topics[:max_topics]


def _assess_importance(analysis: AnalysisResult, duration_seconds: int) -> str:
    """
    Assess session importance based on content richness and duration.

    Args:
        analysis: Analysis results
        duration_seconds: Session duration

    Returns:
        'high', 'medium', or 'low'
    """
    # Count insights
    total_insights = (
        len(analysis.patterns) +
        len(analysis.decisions) +
        len(analysis.learnings) +
        len(analysis.preferences)
    )

    # Calculate insights per hour
    duration_hours = duration_seconds / 3600
    insights_per_hour = total_insights / duration_hours if duration_hours > 0 else 0

    # Assess importance
    if insights_per_hour > 30 or len(analysis.decisions) > 5:
        return 'high'
    elif insights_per_hour > 15 or len(analysis.decisions) > 2:
        return 'medium'
    else:
        return 'low'


def _generate_memory_content(
    analysis: AnalysisResult,
    session_id: str,
    formatted_date: str,
    workspace: Path,
    duration_seconds: int,
    topics: list,
    importance: str
) -> str:
    """Generate memory file content in markdown format."""
    lines = []

    # Frontmatter
    lines.append("---")
    lines.append(f"date: {formatted_date}")
    lines.append(f"topics: [{', '.join(topics)}]")
    lines.append(f"importance: {importance}")
    lines.append(f"type: session-analysis")
    lines.append(f"project: {workspace.name}")
    lines.append(f"reference_count: 0")
    lines.append(f"session_id: {session_id}")
    lines.append(f"duration_minutes: {int(duration_seconds / 60)}")
    lines.append("---")
    lines.append("")

    # Title
    lines.append(f"# Session Analysis - {formatted_date}")
    lines.append("")

    # Session Overview (from first chunk summary if available)
    if analysis.summary:
        lines.append("## Overview")
        lines.append("")
        # Extract first 2-3 sentences from summary
        summary_text = analysis.summary
        if '**Chunk 1**:' in summary_text:
            # Extract first chunk summary
            first_chunk = summary_text.split('**Chunk 2**')[0]
            first_chunk = first_chunk.replace('**Chunk 1**:', '').strip()
            lines.append(first_chunk[:500] + ("..." if len(first_chunk) > 500 else ""))
        else:
            lines.append(summary_text[:500] + ("..." if len(summary_text) > 500 else ""))
        lines.append("")

    # Key Decisions
    if analysis.decisions:
        lines.append("## Key Decisions")
        lines.append("")
        for decision in analysis.decisions:
            lines.append(f"- {decision}")
        lines.append("")

    # Patterns & Insights
    if analysis.patterns:
        lines.append("## Patterns & Insights")
        lines.append("")
        for pattern in analysis.patterns:
            lines.append(f"- {pattern}")
        lines.append("")

    # Key Learnings
    if analysis.learnings:
        lines.append("## Key Learnings")
        lines.append("")
        for learning in analysis.learnings:
            lines.append(f"- {learning}")
        lines.append("")

    # User Preferences
    if analysis.preferences:
        lines.append("## User Preferences & Working Style")
        lines.append("")
        for pref in analysis.preferences:
            lines.append(f"- {pref}")
        lines.append("")

    # TODOs (if any)
    if analysis.todos:
        lines.append("## Action Items")
        lines.append("")
        for todo in analysis.todos:
            # Ensure checkbox format
            if not todo.startswith("- [ ]"):
                todo = f"- [ ] {todo}"
            lines.append(todo)
        lines.append("")

    # Session Metadata
    lines.append("## Session Metadata")
    lines.append("")
    lines.append(f"- **Workspace**: {workspace}")
    lines.append(f"- **Duration**: {int(duration_seconds / 60)} minutes")
    lines.append(f"- **Session ID**: {session_id}")
    lines.append("")

    return "\n".join(lines)
