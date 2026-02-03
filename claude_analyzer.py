#!/usr/bin/env python3
"""
Claude-based conversation analyzer for subconscious processing.

Uses Claude Code CLI in headless mode to analyze terminal recordings.
"""

import subprocess
from pathlib import Path
from typing import Optional

from conversation_analyzer import SubconsciousAnalyzer, AnalysisResult, AnalysisParser


class ClaudeAnalyzer(SubconsciousAnalyzer):
    """Conversation analyzer using Claude Code CLI."""

    def __init__(self, prompt_path: Path, allowed_tools: Optional[list] = None):
        """
        Initialize Claude analyzer.

        Args:
            prompt_path: Path to the analysis prompt file
            allowed_tools: List of tools Claude can use (default: ["Read"])
        """
        super().__init__(prompt_path)
        self.allowed_tools = allowed_tools or ["Read"]

    def analyze(self, recording_path: Path) -> AnalysisResult:
        """
        Analyze a terminal recording using Claude.

        Args:
            recording_path: Path to the parsed terminal recording

        Returns:
            AnalysisResult with extracted insights

        Raises:
            RuntimeError: If Claude invocation fails
            FileNotFoundError: If recording file doesn't exist
        """
        # Read the recording text
        recording_text = self._read_recording(recording_path)

        # Invoke Claude in headless mode
        raw_output = self._invoke_claude(recording_text)

        # Parse the output
        result = AnalysisParser.parse(raw_output)

        return result

    def _invoke_claude(self, recording_text: str) -> str:
        """
        Invoke Claude Code CLI in headless mode.

        Args:
            recording_text: The terminal recording text to analyze

        Returns:
            Raw output from Claude

        Raises:
            RuntimeError: If Claude invocation fails
        """
        # Construct command
        # Note: Using --system-prompt-file for the analysis prompt
        # and passing recording as stdin
        cmd = [
            "claude",
            "--print",  # Headless mode
            "--system-prompt-file", str(self.prompt_path),  # System prompt from file
            "--allowedTools", ",".join(self.allowed_tools),  # Minimal permissions
        ]

        try:
            # Run Claude with recording as stdin
            result = subprocess.run(
                cmd,
                input=recording_text,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                check=True
            )

            return result.stdout

        except subprocess.TimeoutExpired:
            raise RuntimeError("Claude analysis timed out after 5 minutes")

        except subprocess.CalledProcessError as e:
            error_msg = f"Claude invocation failed: {e.stderr}"
            raise RuntimeError(error_msg)

        except FileNotFoundError:
            raise RuntimeError(
                "Claude CLI not found. Is it installed and in PATH?"
            )


def create_analyzer(prompt_path: Path) -> ClaudeAnalyzer:
    """
    Factory function to create a Claude analyzer.

    Args:
        prompt_path: Path to the analysis prompt file

    Returns:
        Configured ClaudeAnalyzer instance
    """
    return ClaudeAnalyzer(
        prompt_path=prompt_path,
        allowed_tools=["Read"]  # Only allow reading files
    )
