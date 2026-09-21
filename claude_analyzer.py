#!/usr/bin/env python3
"""
Claude-based conversation analyzer for subconscious processing.

Uses Claude Code CLI in headless mode to analyze terminal recordings.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional

from conversation_analyzer import SubconsciousAnalyzer, AnalysisResult, AnalysisParser


class ClaudeAnalyzer(SubconsciousAnalyzer):
    """Conversation analyzer using Claude Code CLI."""

    def __init__(self, prompt_path: Path, allowed_tools: Optional[list] = None, output_dir: Optional[Path] = None):
        """
        Initialize Claude analyzer.

        Args:
            prompt_path: Path to the analysis prompt file
            allowed_tools: List of tools Claude can use (default: ["Read"])
            output_dir: Optional directory to save raw LLM output
        """
        super().__init__(prompt_path)
        self.allowed_tools = allowed_tools or ["Read"]
        self.output_dir = output_dir
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)

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

        # Save raw output if output directory is configured
        if self.output_dir:
            # Extract session ID from recording filename (e.g., parsed_20260204_092751.txt)
            session_id = recording_path.stem.replace('parsed_', '')
            output_file = self.output_dir / f'analysis_{session_id}.md'
            output_file.write_text(raw_output)

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
            # Run Claude with recording as stdin.
            # Pass an explicit env so headless (--print) mode gets env-based
            # auth: the CLI's auth gate demands ANTHROPIC_API_KEY or
            # ANTHROPIC_AUTH_TOKEN before making any request, and falls back
            # to stored OAuth credentials (which expire) when neither is set.
            # The Fireworks key keeps the analyzer working independently of
            # the interactive OAuth session.
            result = subprocess.run(
                cmd,
                input=recording_text,
                env=self._build_env(),
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                check=True
            )

            return result.stdout

        except subprocess.TimeoutExpired:
            raise RuntimeError("Claude analysis timed out after 5 minutes")

        except subprocess.CalledProcessError as e:
            error_msg = (
                f"Claude invocation failed with exit code {e.returncode}\n"
                f"Command: {' '.join(cmd)}\n"
                f"STDOUT:\n{e.stdout}\n"
                f"STDERR:\n{e.stderr}"
            )
            raise RuntimeError(error_msg)

        except FileNotFoundError:
            raise RuntimeError(
                "Claude CLI not found. Is it installed and in PATH?"
            )

    @staticmethod
    def _build_env() -> dict:
        """Build the subprocess env, injecting Fireworks auth if needed.

        Mirrors the claude-fireworks shell toggle's key precedence
        (DOX_FIREWORKS_API_KEY first, FIREWORKS_API_KEY fallback). Only
        injects when no explicit Anthropic auth is already in the
        environment, so a user-provided ANTHROPIC_API_KEY or
        ANTHROPIC_AUTH_TOKEN always wins.
        """
        env = os.environ.copy()
        if env.get('ANTHROPIC_API_KEY') or env.get('ANTHROPIC_AUTH_TOKEN'):
            return env
        fireworks_key = env.get('DOX_FIREWORKS_API_KEY') or env.get('FIREWORKS_API_KEY')
        if fireworks_key:
            env['ANTHROPIC_AUTH_TOKEN'] = fireworks_key
        return env


def create_analyzer(prompt_path: Path, output_dir: Optional[Path] = None) -> ClaudeAnalyzer:
    """
    Factory function to create a Claude analyzer.

    Args:
        prompt_path: Path to the analysis prompt file
        output_dir: Optional directory to save raw LLM output

    Returns:
        Configured ClaudeAnalyzer instance
    """
    return ClaudeAnalyzer(
        prompt_path=prompt_path,
        allowed_tools=["Read"],  # Only allow reading files
        output_dir=output_dir
    )
