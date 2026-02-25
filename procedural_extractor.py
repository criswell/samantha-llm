#!/usr/bin/env python3
"""
Procedural memory extractor for subconscious processing.

Analyzes session analysis output to identify procedural patterns —
operational knowledge that should be compiled into reusable runbooks.

This runs as a post-processing step after the main LLM analysis,
using the analysis output (not raw transcript) as input.
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, Callable


def extract_procedural_patterns(
    analysis_file: Path,
    prompt_path: Path,
    output_dir: Path,
    session_id: str,
    log_func: Callable[[str], None]
) -> Optional[Dict[str, Any]]:
    """
    Extract procedural patterns from a session analysis file.

    Args:
        analysis_file: Path to the full analysis markdown file
        prompt_path: Path to the procedural analysis prompt
        output_dir: Directory to write procedural observations
        session_id: Session identifier
        log_func: Logging function

    Returns:
        Parsed procedural observations dict, or None if extraction failed
    """
    if not analysis_file.exists():
        log_func(f"[PROCEDURAL] Analysis file not found: {analysis_file}")
        return None

    if not prompt_path.exists():
        log_func(f"[PROCEDURAL] Prompt not found: {prompt_path}")
        return None

    analysis_text = analysis_file.read_text()
    if not analysis_text.strip():
        log_func("[PROCEDURAL] Analysis file is empty, skipping")
        return None

    # Skip very short analyses (likely failed or trivial sessions)
    if len(analysis_text) < 500:
        log_func(f"[PROCEDURAL] Analysis too short ({len(analysis_text)} chars), skipping")
        return None

    log_func(f"[PROCEDURAL] Analyzing {len(analysis_text):,} chars of session analysis")

    try:
        raw_output = _call_llm(prompt_path, analysis_text, log_func)
    except Exception as e:
        log_func(f"[PROCEDURAL] LLM call failed: {e}")
        return None

    # Parse JSON output
    observations = _parse_output(raw_output, log_func)
    if observations is None:
        return None

    # Check if there were any procedural patterns
    if not observations.get('session_had_procedural_patterns', False):
        log_func("[PROCEDURAL] No procedural patterns detected in this session")
        return observations

    # Write observations to output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f'procedural_{session_id}.json'
    with open(output_file, 'w') as f:
        json.dump(observations, f, indent=2)
    log_func(f"[PROCEDURAL] Wrote observations to: {output_file}")

    # Also save raw LLM output for debugging
    raw_file = output_dir / f'procedural_{session_id}_raw.txt'
    raw_file.write_text(raw_output)

    # Summary
    obs_count = len(observations.get('observations', []))
    rec_count = len(observations.get('runbook_recommendations', []))
    cor_count = len(observations.get('corrections_to_propagate', []))
    log_func(f"[PROCEDURAL] Found {obs_count} observations, {rec_count} recommendations, {cor_count} corrections")

    return observations


def _call_llm(prompt_path: Path, analysis_text: str, log_func: Callable) -> str:
    """
    Call LLM to extract procedural patterns.

    Uses Anthropic API (preferred) or Claude CLI (fallback).
    Uses haiku for cost efficiency — this is a structured extraction task.
    """
    api_key = os.environ.get('ANTHROPIC_API_KEY')

    if api_key:
        return _call_anthropic(prompt_path, analysis_text, api_key, log_func)
    else:
        return _call_claude_cli(prompt_path, analysis_text, log_func)


def _call_anthropic(prompt_path: Path, analysis_text: str, api_key: str, log_func: Callable) -> str:
    """Call Anthropic API for procedural extraction."""
    try:
        from anthropic import Anthropic
    except ImportError:
        raise RuntimeError("anthropic package not installed")

    system_prompt = prompt_path.read_text()

    # Use haiku for cost efficiency — structured extraction doesn't need sonnet
    model = "claude-haiku-4-5-20251001"
    log_func(f"[PROCEDURAL] Using Anthropic API ({model})")

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=4000,
        system=system_prompt,
        messages=[
            {"role": "user", "content": analysis_text}
        ]
    )

    if response.content and len(response.content) > 0:
        return response.content[0].text
    else:
        raise RuntimeError("Empty response from Anthropic API")


def _call_claude_cli(prompt_path: Path, analysis_text: str, log_func: Callable) -> str:
    """Call Claude CLI for procedural extraction."""
    import subprocess
    import tempfile

    log_func("[PROCEDURAL] Using Claude CLI (fallback)")

    # Write analysis to temp file for stdin
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(analysis_text)
        temp_path = f.name

    try:
        result = subprocess.run(
            ['claude', '--print', '--system-prompt-file', str(prompt_path)],
            stdin=open(temp_path),
            capture_output=True,
            text=True,
            timeout=180  # 3 minute timeout for extraction
        )

        if result.returncode != 0:
            raise RuntimeError(f"Claude CLI failed (exit {result.returncode}): {result.stderr}")

        return result.stdout
    finally:
        Path(temp_path).unlink(missing_ok=True)


def _parse_output(raw_output: str, log_func: Callable) -> Optional[Dict[str, Any]]:
    """
    Parse LLM output as JSON.

    Handles cases where the LLM wraps JSON in markdown code fences.
    """
    text = raw_output.strip()

    # Strip markdown code fences if present
    if text.startswith('```'):
        lines = text.split('\n')
        # Remove first line (```json or ```)
        lines = lines[1:]
        # Remove last line (```)
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        text = '\n'.join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        log_func(f"[PROCEDURAL] Failed to parse JSON output: {e}")
        log_func(f"[PROCEDURAL] First 200 chars: {text[:200]}")

        # Try to find JSON object in the output
        start = text.find('{')
        end = text.rfind('}')
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass

        return None
