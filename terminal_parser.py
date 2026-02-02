#!/usr/bin/env python3
"""
Terminal recording parser for samantha-llm subconscious feature.

Parses raw terminal output to extract conversation content.
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional


class TerminalParser:
    """Parse terminal recordings to extract conversation content."""

    # ANSI escape sequence patterns
    ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;?]*[a-zA-Z]')
    ANSI_COLOR = re.compile(r'\x1b\[[\d;]+m')
    ANSI_OSC = re.compile(r'\x1b\][^\x07]*\x07')  # Operating System Command
    ANSI_CSI = re.compile(r'\x1b\[[^a-zA-Z]*[a-zA-Z]')  # Control Sequence Introducer

    # Claude Code UI patterns
    SCRIPT_HEADER = re.compile(r'^Script started on.*\[COMMAND=')
    SCRIPT_FOOTER = re.compile(r'^Script done on.*\[COMMAND_EXIT_CODE=')
    CLAUDE_PROMPT = re.compile(r'❯\s+')

    def __init__(self):
        """Initialize parser."""
        pass

    def strip_ansi(self, text: str) -> str:
        """
        Remove ANSI escape sequences from text.

        Args:
            text: Text with ANSI codes

        Returns:
            Clean text without ANSI codes
        """
        # Remove all ANSI sequences
        text = self.ANSI_OSC.sub('', text)
        text = self.ANSI_CSI.sub('', text)
        text = self.ANSI_ESCAPE.sub('', text)
        text = self.ANSI_COLOR.sub('', text)

        # Remove other control characters except newline/tab
        text = ''.join(char for char in text if char in '\n\t' or ord(char) >= 32)

        return text

    def parse_recording(self, recording_file: Path) -> Dict[str, Any]:
        """
        Parse terminal recording file.

        Args:
            recording_file: Path to terminal recording

        Returns:
            Dictionary with parsed content:
                - raw_text: Full recording text (ANSI stripped)
                - messages: List of conversation messages
                - metadata: Session metadata
        """
        if not recording_file.exists():
            return {
                'raw_text': '',
                'messages': [],
                'metadata': {},
                'error': 'Recording file not found'
            }

        try:
            # Read recording
            with open(recording_file, 'r', encoding='utf-8', errors='replace') as f:
                raw_content = f.read()

            # Strip ANSI codes
            clean_text = self.strip_ansi(raw_content)

            # Extract metadata from script header/footer
            metadata = self._extract_metadata(clean_text)

            # Extract conversation messages (basic - will improve)
            messages = self._extract_messages(clean_text)

            return {
                'raw_text': clean_text,
                'messages': messages,
                'metadata': metadata
            }

        except Exception as e:
            return {
                'raw_text': '',
                'messages': [],
                'metadata': {},
                'error': str(e)
            }

    def _extract_metadata(self, text: str) -> Dict[str, str]:
        """Extract session metadata from script output."""
        metadata = {}

        # Extract from script header
        header_match = self.SCRIPT_HEADER.search(text)
        if header_match:
            header_line = text[header_match.start():header_match.end() + 200]

            # Extract TERM, TTY, COLUMNS, LINES
            for key in ['TERM', 'TTY', 'COLUMNS', 'LINES']:
                pattern = re.compile(rf'{key}="([^"]+)"')
                match = pattern.search(header_line)
                if match:
                    metadata[key.lower()] = match.group(1)

        # Extract from script footer (exit code)
        footer_match = self.SCRIPT_FOOTER.search(text)
        if footer_match:
            footer_line = text[footer_match.start():footer_match.end() + 50]
            exit_code_match = re.search(r'COMMAND_EXIT_CODE="(\d+)"', footer_line)
            if exit_code_match:
                metadata['exit_code'] = exit_code_match.group(1)

        # Extract session statistics (Claude Code specific)
        stats_patterns = {
            'total_cost': re.compile(r'Total cost:\s+\$(\d+\.\d+)'),
            'api_duration': re.compile(r'Total duration \(API\):\s+(.+)'),
            'wall_duration': re.compile(r'Total duration \(wall\):\s+(.+)'),
            'code_changes': re.compile(r'Total code changes:\s+(\d+) lines added, (\d+) lines removed')
        }

        for key, pattern in stats_patterns.items():
            match = pattern.search(text)
            if match:
                if key == 'code_changes':
                    metadata['lines_added'] = match.group(1)
                    metadata['lines_removed'] = match.group(2)
                else:
                    metadata[key] = match.group(1)

        return metadata

    def _extract_messages(self, text: str) -> List[Dict[str, str]]:
        """
        Extract conversation messages from terminal output.

        This is a basic implementation. Will be enhanced in future iterations.
        """
        messages = []

        # For now, just extract lines that look like conversation
        # This is a placeholder - proper parsing requires understanding
        # the specific agent's output format

        # Skip script header/footer
        lines = text.split('\n')
        in_conversation = False
        current_message = []

        for line in lines:
            # Skip script control lines
            if self.SCRIPT_HEADER.match(line) or self.SCRIPT_FOOTER.match(line):
                continue

            # Skip empty lines and pure UI elements
            if not line.strip():
                if current_message:
                    # End of message block
                    messages.append({
                        'type': 'unknown',
                        'content': '\n'.join(current_message)
                    })
                    current_message = []
                continue

            # Accumulate message content
            current_message.append(line)

        # Add final message if any
        if current_message:
            messages.append({
                'type': 'unknown',
                'content': '\n'.join(current_message)
            })

        return messages

    def extract_bootstrap_prompt(self, text: str) -> Optional[str]:
        """Extract bootstrap prompt text from recording."""
        # Bootstrap prompt starts with "# Samantha Hartwell Bootstrap Prompt"
        pattern = re.compile(r'# Samantha Hartwell Bootstrap Prompt.*?(?=\n\s*\n|$)', re.DOTALL)
        match = pattern.search(text)
        if match:
            return match.group(0)
        return None


def parse_terminal_recording(recording_file: Path) -> Dict[str, Any]:
    """
    Convenience function to parse a terminal recording.

    Args:
        recording_file: Path to terminal recording file

    Returns:
        Parsed recording data
    """
    parser = TerminalParser()
    return parser.parse_recording(recording_file)


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python terminal_parser.py <recording_file>")
        sys.exit(1)

    recording_file = Path(sys.argv[1])
    result = parse_terminal_recording(recording_file)

    print(f"Parsed {recording_file.name}")
    print(f"  Messages found: {len(result['messages'])}")
    print(f"  Metadata: {result['metadata']}")
    print(f"  Text length: {len(result['raw_text'])} chars")

    if result.get('error'):
        print(f"  Error: {result['error']}")
