#!/usr/bin/env python3
"""
Quick test for memory generation with session workspaces.
"""

import tempfile
import shutil
from pathlib import Path
from session_workspace import SessionWorkspace
from conversation_analyzer import AnalysisResult
from memory_generator import generate_memory_file


def test_memory_generation_with_workspace():
    """Test memory generation writes to session workspace."""
    # Create temp cerebrum
    temp_dir = tempfile.mkdtemp()
    cerebrum_path = Path(temp_dir) / 'cerebrum'
    cerebrum_path.mkdir()

    try:
        # Create session workspace
        session_id = '20260205_120000'
        workspace = SessionWorkspace(session_id, cerebrum_path)
        workspace.create()

        # Create mock analysis
        analysis = AnalysisResult(
            patterns=['Test pattern 1', 'Test pattern 2'],
            decisions=['Test decision: rationale'],
            todos=['Test TODO'],
            preferences=['Test preference'],
            learnings=['Test learning'],
            summary='Test session summary'
        )

        # Generate memory file with workspace
        memory_file = generate_memory_file(
            analysis=analysis,
            session_id=session_id,
            workspace=Path('/test/workspace'),
            duration_seconds=900,  # 15 minutes
            cerebrum_path=cerebrum_path,
            session_workspace=workspace
        )

        # Verify memory file is in session workspace
        assert memory_file.exists(), f"Memory file not created: {memory_file}"
        assert memory_file.parent == workspace.memories_dir, \
            f"Memory file in wrong location: {memory_file.parent} != {workspace.memories_dir}"

        # Verify content
        content = memory_file.read_text()
        assert 'Test pattern 1' in content, "Pattern not in memory file"
        assert 'Test decision' in content, "Decision not in memory file"
        assert session_id in content, "Session ID not in memory file"

        print("✓ Memory file created in session workspace")
        print(f"  Location: {memory_file}")
        print(f"  Size: {len(content)} bytes")
        print()
        print("✓ All tests passed!")

    finally:
        shutil.rmtree(temp_dir)


def test_memory_generation_legacy():
    """Test memory generation without workspace (legacy mode)."""
    # Create temp cerebrum
    temp_dir = tempfile.mkdtemp()
    cerebrum_path = Path(temp_dir) / 'cerebrum'
    cerebrum_path.mkdir()

    try:
        # Create mock analysis
        analysis = AnalysisResult(
            patterns=['Test pattern'],
            decisions=['Test decision'],
            todos=[],
            preferences=[],
            learnings=[],
            summary='Test'
        )

        # Generate memory file WITHOUT workspace (legacy)
        memory_file = generate_memory_file(
            analysis=analysis,
            session_id='20260205_120000',
            workspace=Path('/test/workspace'),
            duration_seconds=900,
            cerebrum_path=cerebrum_path,
            session_workspace=None  # No workspace = legacy mode
        )

        # Verify memory file is in cerebrum short-term memory
        expected_dir = cerebrum_path / '.ai' / 'short-term-memory'
        assert memory_file.exists(), "Memory file not created"
        assert memory_file.parent == expected_dir, \
            f"Memory file in wrong location: {memory_file.parent} != {expected_dir}"

        print("✓ Legacy mode: Memory file created in cerebrum")
        print(f"  Location: {memory_file}")
        print()

    finally:
        shutil.rmtree(temp_dir)


if __name__ == '__main__':
    print("Testing memory generation integration...\n")
    test_memory_generation_with_workspace()
    test_memory_generation_legacy()
    print("\n✅ All integration tests passed!")
