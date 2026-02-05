#!/usr/bin/env python3
"""
Conversation analysis abstraction layer for subconscious processing.

Provides base classes and data structures for analyzing terminal recordings
using different LLM agents (Claude, Abacus.ai, Copilot).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import re


@dataclass
class AnalysisResult:
    """Structured result from conversation analysis."""

    patterns: List[str] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)
    todos: List[str] = field(default_factory=list)
    preferences: List[str] = field(default_factory=list)
    learnings: List[str] = field(default_factory=list)
    summary: Optional[str] = None

    def is_empty(self) -> bool:
        """Check if analysis found anything."""
        return not any([
            self.patterns,
            self.decisions,
            self.todos,
            self.preferences,
            self.learnings
        ])

    def to_context_summary(self) -> str:
        """
        Generate concise context summary for passing to next chunk.

        Used in chunked analysis to preserve context across boundaries.
        """
        lines = []

        lines.append("## Previous Context")
        lines.append("")

        if self.summary:
            lines.append(f"**Summary**: {self.summary}")
            lines.append("")

        if self.decisions:
            lines.append("**Key Decisions:**")
            for decision in self.decisions[:3]:  # Top 3 decisions
                lines.append(f"- {decision}")
            lines.append("")

        if self.patterns:
            lines.append("**Observed Patterns:**")
            for pattern in self.patterns[:3]:  # Top 3 patterns
                lines.append(f"- {pattern}")
            lines.append("")

        if self.todos:
            lines.append("**Pending Items:**")
            for todo in self.todos[:3]:  # Top 3 TODOs
                lines.append(f"- {todo}")
            lines.append("")

        return "\n".join(lines)

    def to_markdown(self) -> str:
        """Convert to markdown format."""
        sections = []

        sections.append("# Conversation Analysis\n")

        if self.patterns:
            sections.append("## Patterns")
            for item in self.patterns:
                sections.append(f"- {item}")
            sections.append("")

        if self.decisions:
            sections.append("## Decisions")
            for item in self.decisions:
                sections.append(f"- {item}")
            sections.append("")

        if self.todos:
            sections.append("## TODOs")
            for item in self.todos:
                # Ensure checkbox format
                if not item.startswith("- [ ]"):
                    item = f"- [ ] {item}" if not item.startswith("-") else item.replace("-", "- [ ]", 1)
                sections.append(item)
            sections.append("")

        if self.preferences:
            sections.append("## Preferences")
            for item in self.preferences:
                sections.append(f"- {item}")
            sections.append("")

        if self.learnings:
            sections.append("## Learnings")
            for item in self.learnings:
                sections.append(f"- {item}")
            sections.append("")

        if self.summary:
            sections.append("## Summary")
            sections.append(self.summary)
            sections.append("")

        return "\n".join(sections)


class AnalysisParser:
    """Parses LLM output (markdown or JSON) into structured AnalysisResult."""

    @staticmethod
    def parse(raw_output: str) -> AnalysisResult:
        """
        Parse LLM output into AnalysisResult.

        Handles both markdown-formatted output and JSON output.
        """
        # Try JSON first (if agent supports it)
        if raw_output.strip().startswith('{'):
            return AnalysisParser._parse_json(raw_output)

        # Otherwise parse as markdown
        return AnalysisParser._parse_markdown(raw_output)

    @staticmethod
    def _parse_json(json_output: str) -> AnalysisResult:
        """Parse JSON-formatted analysis output."""
        import json
        try:
            data = json.loads(json_output)
            return AnalysisResult(
                patterns=data.get('patterns', []),
                decisions=data.get('decisions', []),
                todos=data.get('todos', []),
                preferences=data.get('preferences', []),
                learnings=data.get('learnings', []),
                summary=data.get('summary')
            )
        except json.JSONDecodeError:
            # Fallback to markdown parsing
            return AnalysisParser._parse_markdown(json_output)

    @staticmethod
    def _parse_markdown(markdown_output: str) -> AnalysisResult:
        """Parse markdown-formatted analysis output."""
        result = AnalysisResult()

        # Split into sections
        sections = AnalysisParser._extract_sections(markdown_output)

        # Parse each section (with fallback to alternative names)
        result.patterns = AnalysisParser._extract_list_items(
            sections.get('patterns', '')
        )
        result.decisions = AnalysisParser._extract_list_items(
            sections.get('key decisions', sections.get('decisions', ''))
        )
        result.todos = AnalysisParser._extract_list_items(
            sections.get('action items & todos (detailed)', sections.get('todos', ''))
        )
        result.preferences = AnalysisParser._extract_list_items(
            sections.get('user preferences', sections.get('preferences', ''))
        )
        result.learnings = AnalysisParser._extract_list_items(
            sections.get('key learnings', sections.get('learnings', ''))
        )
        result.summary = (sections.get('session summary', sections.get('summary', '')) or '').strip() or None

        return result

    @staticmethod
    def _extract_sections(text: str) -> dict:
        """
        Extract markdown sections by heading.

        Handles two structures:
        1. Hierarchical (from raw LLM output):
           - ## Part 2: High-Level Insights
             - ### Patterns
             - ### Key Decisions
        2. Flat (from to_markdown() output):
           - ## Patterns
           - ## Decisions

        Extracts both level 2 (##) and level 3 (###) headings.
        """
        sections = {}
        current_section = None
        current_subsection = None
        current_content = []
        in_part2 = False

        for line in text.split('\n'):
            # Check for level 2 headings (##)
            heading_match = re.match(r'^##\s+(.+)$', line)
            if heading_match:
                # Save previous subsection/section
                if current_subsection:
                    sections[current_subsection] = '\n'.join(current_content)
                    current_subsection = None
                    current_content = []
                elif current_section and current_content:
                    # Only save if not a Part 2 container
                    if not in_part2 or 'part 2' not in current_section:
                        sections[current_section] = '\n'.join(current_content)
                    current_content = []

                # Check if this is Part 2
                heading = heading_match.group(1).lower()
                in_part2 = 'part 2' in heading

                # For non-Part 2 headings, treat as sections
                if not in_part2:
                    current_section = heading
                else:
                    current_section = heading
                continue

            # Check for level 3 headings (###)
            subheading_match = re.match(r'^###\s+(.+)$', line)
            if subheading_match:
                # Save previous subsection
                if current_subsection:
                    sections[current_subsection] = '\n'.join(current_content)
                    current_content = []

                # Start new subsection (only when in Part 2)
                if in_part2:
                    current_subsection = subheading_match.group(1).lower()
                continue

            # Accumulate content
            if current_subsection or current_section:
                current_content.append(line)

        # Save last subsection/section
        if current_subsection:
            sections[current_subsection] = '\n'.join(current_content)
        elif current_section and current_content:
            if not in_part2 or 'part 2' not in current_section:
                sections[current_section] = '\n'.join(current_content)

        return sections

    @staticmethod
    def _extract_list_items(section_text: str) -> List[str]:
        """Extract list items from a section."""
        items = []

        for line in section_text.split('\n'):
            line = line.strip()

            # Skip empty lines and "None identified" markers
            if not line or 'none identified' in line.lower():
                continue

            # Extract list items (-, *, [ ])
            if line.startswith('- ') or line.startswith('* ') or line.startswith('- [ ]'):
                # Remove list marker
                item = re.sub(r'^[-*]\s+(\[\s*\]\s*)?', '', line)
                if item:
                    items.append(item)

        return items


class SubconsciousAnalyzer(ABC):
    """Abstract base class for conversation analyzers."""

    def __init__(self, prompt_path: Path):
        """
        Initialize analyzer with analysis prompt.

        Args:
            prompt_path: Path to the system prompt file
        """
        self.prompt_path = prompt_path
        if not prompt_path.exists():
            raise FileNotFoundError(f"Analysis prompt not found: {prompt_path}")

    @abstractmethod
    def analyze(self, recording_path: Path) -> AnalysisResult:
        """
        Analyze a terminal recording and extract insights.

        Args:
            recording_path: Path to the parsed terminal recording text file

        Returns:
            AnalysisResult with extracted insights
        """
        pass

    def _read_prompt(self) -> str:
        """Read the analysis prompt from file."""
        return self.prompt_path.read_text()

    def _read_recording(self, recording_path: Path) -> str:
        """Read the terminal recording text."""
        if not recording_path.exists():
            raise FileNotFoundError(f"Recording not found: {recording_path}")
        return recording_path.read_text()
