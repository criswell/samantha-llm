#!/usr/bin/env python3
"""
Tests for local memory search fallback.
"""

import contextlib
import importlib.machinery
import importlib.util
import io
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


def load_cli_module():
    """Load the extensionless samantha-llm script as a module."""
    script_path = Path(__file__).parent / 'samantha-llm'
    loader = importlib.machinery.SourceFileLoader(
        'samantha_llm_cli_memory_search_test',
        str(script_path),
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class TestMemorySearchFallback(unittest.TestCase):
    """Tests for qmd-free memory search."""

    def setUp(self):
        self.cli = load_cli_module()
        self.temp_dir = tempfile.mkdtemp()
        self.cerebrum = Path(self.temp_dir) / 'cerebrum'
        self.memory_dir = (
            self.cerebrum / '.ai' / 'short-term-memory' / '.ai'
        )
        self.memory_dir.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def write_memory(self, filename, title, body, frontmatter=''):
        content = f"""---
date: 2026-05-27
topics: [{frontmatter}]
importance: high
type: technical
---

# {title}

{body}
"""
        path = self.memory_dir / filename
        path.write_text(content)
        return path

    def run_search(self, query, qmd_bin=None, qmd_result=None):
        output = io.StringIO()
        with patch.object(self.cli, 'get_repo_dir', return_value=self.cerebrum), \
             patch.object(self.cli, 'get_qmd_bin_path', return_value=qmd_bin), \
             contextlib.redirect_stdout(output):
            if qmd_result is None:
                result = self.cli.search_memories(query)
            else:
                with patch.object(
                    self.cli.subprocess,
                    'run',
                    return_value=qmd_result,
                ):
                    result = self.cli.search_memories(query)

        return result, output.getvalue()

    def test_missing_qmd_uses_local_keyword_fallback(self):
        self.write_memory(
            '2026-05-27_cache_failure.md',
            'Cache Failure Handling',
            'Use a boring fallback when the external search tool fails.',
            'memory-search, fallback',
        )

        result, output = self.run_search('cache fallback')

        self.assertTrue(result)
        self.assertIn('qmd is not installed', output)
        self.assertIn('Local Memory Search Results', output)
        self.assertIn('Cache Failure Handling', output)
        self.assertIn('2026-05-27_cache_failure.md', output)

    def test_qmd_failure_uses_local_keyword_fallback(self):
        self.write_memory(
            '2026-05-27_index_repair.md',
            'Index Repair',
            'Fallback search still works when the qmd collection is missing.',
            'memory-search',
        )
        qmd_result = subprocess.CompletedProcess(
            ['qmd'],
            1,
            stdout='',
            stderr='collection not found',
        )

        result, output = self.run_search(
            'collection missing',
            qmd_bin='/tmp/qmd',
            qmd_result=qmd_result,
        )

        self.assertTrue(result)
        self.assertIn('qmd search failed', output)
        self.assertIn('Local Memory Search Results', output)
        self.assertIn('Index Repair', output)

    def test_local_search_reports_no_results(self):
        self.write_memory(
            '2026-05-27_api_notes.md',
            'API Notes',
            'Document ordinary request and response behavior.',
            'api',
        )

        result, output = self.run_search('nonexistent query')

        self.assertTrue(result)
        self.assertIn('No results found', output)
        self.assertIn('local keyword fallback', output)

    def test_title_matches_rank_ahead_of_body_only_matches(self):
        self.write_memory(
            '2026-05-27_body_only.md',
            'General Notes',
            'This body mentions local fallback search once.',
            'notes',
        )
        self.write_memory(
            '2026-05-27_local_fallback.md',
            'Local Fallback Search',
            'A short memory about resilience.',
            'memory-search',
        )

        result, output = self.run_search('local fallback')

        self.assertTrue(result)
        self.assertLess(
            output.find('Local Fallback Search'),
            output.find('General Notes'),
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)
