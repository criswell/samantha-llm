#!/usr/bin/env python3
"""
Analyzer provider selection for subconscious processing.

Keeps provider fallback behavior consistent across first-pass processing and
chunk retry.
"""

import os
import shutil
from pathlib import Path
from typing import Optional

try:
    import anthropic_analyzer
    HAS_ANTHROPIC_ANALYZER = True
except Exception:
    anthropic_analyzer = None
    HAS_ANTHROPIC_ANALYZER = False

try:
    import claude_analyzer
    HAS_CLAUDE_ANALYZER = True
except Exception:
    claude_analyzer = None
    HAS_CLAUDE_ANALYZER = False

try:
    import codex_analyzer
    HAS_CODEX_ANALYZER = True
except Exception:
    codex_analyzer = None
    HAS_CODEX_ANALYZER = False


def codex_available() -> bool:
    """Return True when the Codex analyzer module and CLI are available."""
    return HAS_CODEX_ANALYZER and shutil.which('codex') is not None


def has_available_analyzer() -> bool:
    """Return True if any analyzer backend can plausibly run."""
    return (
        (HAS_ANTHROPIC_ANALYZER and bool(os.environ.get('ANTHROPIC_API_KEY'))) or
        HAS_CLAUDE_ANALYZER or
        codex_available()
    )


def create_named_analyzer(name: str, prompt_path: Path, output_dir: Optional[Path] = None):
    """Create a specific analyzer backend by name."""
    normalized = name.strip().lower().replace('_', '-')

    if normalized in ('anthropic', 'anthropic-api', 'claude-api'):
        if not HAS_ANTHROPIC_ANALYZER:
            raise RuntimeError("Anthropic analyzer module is not available")
        if not os.environ.get('ANTHROPIC_API_KEY'):
            raise RuntimeError("ANTHROPIC_API_KEY is required for the Anthropic analyzer")
        return anthropic_analyzer.create_analyzer(prompt_path, output_dir=output_dir)

    if normalized in ('claude', 'claude-cli'):
        if not HAS_CLAUDE_ANALYZER:
            raise RuntimeError("Claude analyzer module is not available")
        return claude_analyzer.create_analyzer(prompt_path, output_dir=output_dir)

    if normalized in ('codex', 'openai-codex'):
        if not HAS_CODEX_ANALYZER:
            raise RuntimeError("Codex analyzer module is not available")
        if not codex_available():
            raise RuntimeError("Codex CLI not found. Is it installed and in PATH?")
        return codex_analyzer.create_analyzer(prompt_path, output_dir=output_dir)

    raise RuntimeError(
        f"Unknown analyzer '{name}'. Supported analyzers: anthropic, claude, codex"
    )


def create_best_analyzer(prompt_path: Path, output_dir: Optional[Path] = None, agent: str = 'claude'):
    """
    Create the best available analyzer with fallback logic.

    Priority:
    1. SAMANTHA_ANALYZER if explicitly set
    2. Anthropic API when ANTHROPIC_API_KEY is available
    3. Codex CLI for Codex sessions
    4. Claude CLI
    5. Codex CLI as a final generic fallback
    """
    requested = os.environ.get('SAMANTHA_ANALYZER', '').strip()
    if requested and requested.lower() != 'auto':
        return create_named_analyzer(requested, prompt_path, output_dir)

    if HAS_ANTHROPIC_ANALYZER and os.environ.get('ANTHROPIC_API_KEY'):
        return anthropic_analyzer.create_analyzer(prompt_path, output_dir=output_dir)

    if agent.lower() == 'codex' and codex_available():
        return codex_analyzer.create_analyzer(prompt_path, output_dir=output_dir)

    if HAS_CLAUDE_ANALYZER:
        return claude_analyzer.create_analyzer(prompt_path, output_dir=output_dir)

    if codex_available():
        return codex_analyzer.create_analyzer(prompt_path, output_dir=output_dir)

    raise RuntimeError(
        "No LLM analyzer available. Options:\n"
        "1. Set ANTHROPIC_API_KEY environment variable to use Anthropic API\n"
        "2. Install Claude CLI (claude command) and ensure it's in PATH\n"
        "3. Install Codex CLI (codex command) and ensure it's in PATH\n"
        "4. Install anthropic package: pip install anthropic"
    )
