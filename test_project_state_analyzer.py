#!/usr/bin/env python3
"""
Tests for project_state_analyzer.py

Basic smoke tests to verify the analyzer works correctly.
"""

import json
import tempfile
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent))

from project_state_analyzer import ProjectStateAnalyzer, ProjectUpdate


def test_analyzer_initialization():
    """Test that analyzer initializes correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cerebrum_path = Path(tmpdir)
        analyzer = ProjectStateAnalyzer(cerebrum_path)
        
        assert analyzer.cerebrum_path == cerebrum_path
        assert analyzer.pending_updates_path.exists()
        print("✓ Analyzer initialization test passed")


def test_load_current_tasks():
    """Test loading current tasks index."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cerebrum_path = Path(tmpdir)
        analyzer = ProjectStateAnalyzer(cerebrum_path)
        
        current_tasks_path = cerebrum_path / '.ai' / 'current-tasks' / '.ai'
        current_tasks_path.mkdir(parents=True, exist_ok=True)
        
        index_file = current_tasks_path / 'index.json'
        test_data = {
            "active": [
                {"name": "test-project", "status": "In Progress"}
            ]
        }
        
        with open(index_file, 'w') as f:
            json.dump(test_data, f)
        
        tasks = analyzer.load_current_tasks()
        assert len(tasks['active']) == 1
        assert tasks['active'][0]['name'] == 'test-project'
        print("✓ Load current tasks test passed")


def test_find_matching_project():
    """Test finding matching project by workspace name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cerebrum_path = Path(tmpdir)
        analyzer = ProjectStateAnalyzer(cerebrum_path)
        
        current_tasks = {
            "active": [
                {"name": "test-project", "status": "In Progress"},
                {"name": "other-project", "status": "Complete"}
            ]
        }
        
        project = analyzer._find_matching_project("test-project", current_tasks)
        assert project is not None
        assert project['name'] == 'test-project'
        
        project = analyzer._find_matching_project("nonexistent", current_tasks)
        assert project is None
        
        print("✓ Find matching project test passed")


def test_extract_evidence_from_llm():
    """Test extracting evidence from LLM analysis."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cerebrum_path = Path(tmpdir)
        analyzer = ProjectStateAnalyzer(cerebrum_path)
        
        llm_analysis = {
            "decisions": [
                "Phase 3 is complete and ready for testing",
                "Implemented new feature X"
            ],
            "patterns": [
                "User frequently tests after implementation"
            ],
            "summary": "Session completed Phase 3 implementation"
        }
        
        evidence = analyzer._extract_evidence_from_llm(llm_analysis)
        assert len(evidence) > 0
        assert any('complete' in e.lower() for e in evidence)
        print("✓ Extract evidence from LLM test passed")


def test_calculate_confidence():
    """Test confidence calculation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cerebrum_path = Path(tmpdir)
        analyzer = ProjectStateAnalyzer(cerebrum_path)
        
        assert analyzer._calculate_confidence([]) == "low"
        assert analyzer._calculate_confidence(["e1", "e2"]) == "low"
        assert analyzer._calculate_confidence(["e1", "e2", "e3"]) == "medium"
        assert analyzer._calculate_confidence(["e1", "e2", "e3", "e4", "e5"]) == "high"
        print("✓ Calculate confidence test passed")


def test_save_pending_update():
    """Test saving pending update to file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cerebrum_path = Path(tmpdir)
        analyzer = ProjectStateAnalyzer(cerebrum_path)
        
        update = ProjectUpdate(
            session_id="20260205_143022",
            session_date="2026-02-05",
            project_name="test-project",
            confidence="high",
            proposed_changes={"status": "Complete"},
            reasoning="Tests passed",
            evidence=["Test evidence"]
        )
        
        filepath = analyzer.save_pending_update(update)
        assert filepath.exists()
        assert filepath.name == "20260205_143022_test-project.json"
        
        with open(filepath) as f:
            saved_data = json.load(f)
        
        assert saved_data['project_name'] == 'test-project'
        assert saved_data['confidence'] == 'high'
        print("✓ Save pending update test passed")


def test_project_update_to_dict():
    """Test ProjectUpdate serialization."""
    update = ProjectUpdate(
        session_id="20260205_143022",
        session_date="2026-02-05",
        project_name="test-project",
        confidence="medium",
        proposed_changes={"status": "In Progress"},
        reasoning="Work ongoing",
        evidence=["Evidence 1", "Evidence 2"]
    )
    
    data = update.to_dict()
    assert data['session_id'] == "20260205_143022"
    assert data['project_name'] == "test-project"
    assert len(data['evidence']) == 2
    
    json_str = update.to_json()
    assert isinstance(json_str, str)
    assert "test-project" in json_str
    print("✓ ProjectUpdate serialization test passed")


def run_all_tests():
    """Run all tests."""
    print("Running project_state_analyzer tests...\n")
    
    test_analyzer_initialization()
    test_load_current_tasks()
    test_find_matching_project()
    test_extract_evidence_from_llm()
    test_calculate_confidence()
    test_save_pending_update()
    test_project_update_to_dict()
    
    print("\n✅ All tests passed!")


if __name__ == '__main__':
    run_all_tests()
