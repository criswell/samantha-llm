#!/usr/bin/env python3
"""
Anthropic API-based conversation analyzer for subconscious processing.

Uses Anthropic Python SDK to analyze terminal recordings.
Works with sessions from any interface (Claude Code, Abacus.ai, etc.).
"""

import os
from pathlib import Path
from typing import Optional

from conversation_analyzer import SubconsciousAnalyzer, AnalysisResult, AnalysisParser


class AnthropicAnalyzer(SubconsciousAnalyzer):
    """Conversation analyzer using Anthropic API."""

    def __init__(self, prompt_path: Path, api_key: Optional[str] = None, 
                 model: str = "claude-sonnet-4-20250514", output_dir: Optional[Path] = None):
        """
        Initialize Anthropic analyzer.

        Args:
            prompt_path: Path to the analysis prompt file
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Model to use for analysis
            output_dir: Optional directory to save raw LLM output
        """
        super().__init__(prompt_path)
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment or provided")
        
        self.model = model
        self.output_dir = output_dir
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)

    def analyze(self, recording_path: Path) -> AnalysisResult:
        """
        Analyze a terminal recording using Anthropic API.

        Args:
            recording_path: Path to the parsed terminal recording

        Returns:
            AnalysisResult with extracted insights

        Raises:
            RuntimeError: If API call fails
            FileNotFoundError: If recording file doesn't exist
        """
        # Read the recording text
        recording_text = self._read_recording(recording_path)

        # Read the analysis prompt
        system_prompt = self._read_prompt()

        # Call Anthropic API
        raw_output = self._call_anthropic_api(system_prompt, recording_text)

        # Save raw output if output directory is configured
        if self.output_dir:
            # Extract session ID from recording filename
            session_id = recording_path.stem.replace('parsed_', '')
            output_file = self.output_dir / f'analysis_{session_id}.md'
            output_file.write_text(raw_output)

        # Parse the output
        result = AnalysisParser.parse(raw_output)

        return result

    def _call_anthropic_api(self, system_prompt: str, user_message: str) -> str:
        """
        Call Anthropic API to analyze the recording.

        Args:
            system_prompt: System prompt for analysis
            user_message: Terminal recording text to analyze

        Returns:
            Raw output from the API

        Raises:
            RuntimeError: If API call fails
        """
        try:
            from anthropic import Anthropic
        except ImportError:
            raise RuntimeError(
                "anthropic package not installed. Install with: pip install anthropic"
            )

        try:
            client = Anthropic(api_key=self.api_key)
            
            response = client.messages.create(
                model=self.model,
                max_tokens=16000,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )

            # Extract text from response
            if response.content and len(response.content) > 0:
                return response.content[0].text
            else:
                raise RuntimeError("Empty response from Anthropic API")

        except Exception as e:
            error_msg = (
                f"Anthropic API call failed: {e}\n"
                f"Model: {self.model}\n"
                f"Recording length: {len(user_message):,} chars"
            )
            raise RuntimeError(error_msg)


def create_analyzer(prompt_path: Path, api_key: Optional[str] = None,
                   model: str = "claude-sonnet-4-20250514",
                   output_dir: Optional[Path] = None) -> AnthropicAnalyzer:
    """
    Factory function to create an Anthropic analyzer.

    Args:
        prompt_path: Path to the analysis prompt file
        api_key: Optional API key (uses ANTHROPIC_API_KEY env var if not provided)
        model: Model to use for analysis
        output_dir: Optional directory to save raw LLM output

    Returns:
        Configured AnthropicAnalyzer instance
    """
    return AnthropicAnalyzer(
        prompt_path=prompt_path,
        api_key=api_key,
        model=model,
        output_dir=output_dir
    )
