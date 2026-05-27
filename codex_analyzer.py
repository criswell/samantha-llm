#!/usr/bin/env python3
"""
Codex-based conversation analyzer for subconscious processing.

Uses OpenAI Codex CLI in non-interactive mode to analyze terminal recordings.
"""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from conversation_analyzer import SubconsciousAnalyzer, AnalysisResult, AnalysisParser


ANALYSIS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "patterns": {"type": "array", "items": {"type": "string"}},
        "decisions": {"type": "array", "items": {"type": "string"}},
        "todos": {"type": "array", "items": {"type": "string"}},
        "preferences": {"type": "array", "items": {"type": "string"}},
        "learnings": {"type": "array", "items": {"type": "string"}},
        "summary": {"type": "string"},
    },
    "required": [
        "patterns",
        "decisions",
        "todos",
        "preferences",
        "learnings",
        "summary",
    ],
}


class CodexAnalyzer(SubconsciousAnalyzer):
    """Conversation analyzer using OpenAI Codex CLI."""

    def __init__(self, prompt_path: Path, output_dir: Optional[Path] = None):
        """
        Initialize Codex analyzer.

        Args:
            prompt_path: Path to the analysis prompt file
            output_dir: Optional directory to save raw LLM output
        """
        super().__init__(prompt_path)
        self.output_dir = output_dir
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)

    def analyze(self, recording_path: Path) -> AnalysisResult:
        """
        Analyze a terminal recording using Codex.

        Args:
            recording_path: Path to the parsed terminal recording

        Returns:
            AnalysisResult with extracted insights

        Raises:
            RuntimeError: If Codex invocation fails
            FileNotFoundError: If recording file doesn't exist
        """
        recording_text = self._read_recording(recording_path)
        system_prompt = self._read_prompt()
        raw_output = self._invoke_codex(system_prompt, recording_text)

        if self.output_dir:
            session_id = recording_path.stem.replace('parsed_', '')
            output_file = self.output_dir / f'analysis_{session_id}.md'
            output_file.write_text(raw_output)

        return AnalysisParser.parse(raw_output)

    def _invoke_codex(self, system_prompt: str, recording_text: str) -> str:
        """
        Invoke Codex CLI in non-interactive mode.

        Args:
            system_prompt: Analysis instructions
            recording_text: The terminal recording text to analyze

        Returns:
            Raw JSON output from Codex

        Raises:
            RuntimeError: If Codex invocation fails
        """
        schema_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.schema.json',
            prefix='samantha_codex_analysis_',
            encoding='utf-8',
            delete=False,
        )
        output_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.json',
            prefix='samantha_codex_output_',
            encoding='utf-8',
            delete=False,
        )

        schema_path = Path(schema_file.name)
        output_path = Path(output_file.name)

        try:
            json.dump(ANALYSIS_SCHEMA, schema_file)
            schema_file.close()
            output_file.close()

            prompt = self._build_prompt(system_prompt, recording_text)
            cmd = [
                'codex',
                '--ask-for-approval',
                'never',
                'exec',
                '--sandbox',
                'read-only',
                '--skip-git-repo-check',
                '--output-schema',
                str(schema_path),
                '--output-last-message',
                str(output_path),
                '--json',
                '--color',
                'never',
                '-',
            ]

            result = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"Codex invocation failed with exit code {result.returncode}\n"
                    f"Command: {' '.join(cmd)}\n"
                    f"STDOUT:\n{result.stdout}\n"
                    f"STDERR:\n{result.stderr}"
                )

            raw_output = output_path.read_text(encoding='utf-8').strip()
            if not raw_output:
                raw_output = self._extract_last_message_from_jsonl(result.stdout)

            if not raw_output:
                raise RuntimeError("Codex returned no final analysis output")

            return raw_output

        except subprocess.TimeoutExpired:
            raise RuntimeError("Codex analysis timed out after 5 minutes")
        except FileNotFoundError:
            raise RuntimeError("Codex CLI not found. Is it installed and in PATH?")
        finally:
            for temp_path in (schema_path, output_path):
                try:
                    temp_path.unlink(missing_ok=True)
                except TypeError:
                    if temp_path.exists():
                        temp_path.unlink()

    def _build_prompt(self, system_prompt: str, recording_text: str) -> str:
        """Build a single stdin prompt for Codex exec."""
        return (
            f"{system_prompt.rstrip()}\n\n"
            "Return only JSON matching the provided output schema. "
            "Do not modify files or run commands; analyze only the text below.\n\n"
            "---\n\n"
            f"{recording_text}"
        )

    def _extract_last_message_from_jsonl(self, jsonl_output: str) -> str:
        """Best-effort fallback for Codex JSONL stdout."""
        last_message = ''
        for line in jsonl_output.splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            message = event.get('message') or event.get('content')
            if isinstance(message, str):
                last_message = message
            elif isinstance(message, dict):
                content = message.get('content') or message.get('text')
                if isinstance(content, str):
                    last_message = content

        return last_message.strip()


def create_analyzer(prompt_path: Path, output_dir: Optional[Path] = None) -> CodexAnalyzer:
    """
    Factory function to create a Codex analyzer.

    Args:
        prompt_path: Path to the analysis prompt file
        output_dir: Optional directory to save raw LLM output

    Returns:
        Configured CodexAnalyzer instance
    """
    return CodexAnalyzer(prompt_path=prompt_path, output_dir=output_dir)
