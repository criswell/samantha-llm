#!/usr/bin/env python3
"""
Project state analyzer for subconscious system.

Detects when project state has changed during a session and generates
draft updates for user review.
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class ProjectUpdate:
    """Represents a proposed project state update."""
    session_id: str
    session_date: str
    project_name: str
    confidence: str
    proposed_changes: Dict[str, Optional[str]]
    reasoning: str
    evidence: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class ProjectStateAnalyzer:
    """Analyzes session data to detect project state changes."""

    COMPLETION_KEYWORDS = [
        r'\b(complete|completed|done|finished|merged|deployed|shipped)\b',
        r'\b(phase \d+ complete)\b',
        r'\b(ticket \d+\.\d+ complete)\b',
        r'\b(all tests passing)\b',
        r'\b(ready for (testing|review|production))\b',
    ]

    PROGRESS_KEYWORDS = [
        r'\b(implemented|added|created|built|fixed|refactored)\b',
        r'\b(working on|in progress|started)\b',
        r'\b(phase \d+)\b',
        r'\b(ticket \d+\.\d+)\b',
    ]

    BLOCKER_KEYWORDS = [
        r'\b(blocked|blocker|stuck|waiting for|dependency)\b',
        r'\b(failed|failing|broken|error)\b',
        r'\b(need to|must|required)\b',
    ]

    def __init__(self, cerebrum_path: Path):
        """
        Initialize analyzer.

        Args:
            cerebrum_path: Path to cerebrum root directory
        """
        self.cerebrum_path = cerebrum_path
        self.current_tasks_path = cerebrum_path / '.ai' / 'current-tasks' / '.ai'
        self.pending_updates_path = self.current_tasks_path / 'pending-updates'
        self.pending_updates_path.mkdir(parents=True, exist_ok=True)

    def load_current_tasks(self) -> Dict[str, Any]:
        """Load current tasks index."""
        index_file = self.current_tasks_path / 'index.json'
        if not index_file.exists():
            return {"active": [], "recently_completed": []}

        with open(index_file) as f:
            return json.load(f)

    def analyze_session(
        self,
        session_id: str,
        workspace: Path,
        analysis_result: Optional[Any] = None,
        terminal_data: Optional[Dict] = None,
        llm_analysis: Optional[Dict] = None
    ) -> List[ProjectUpdate]:
        """
        Analyze session for project state changes.

        Args:
            session_id: Session identifier (YYYYMMDD_HHMMSS)
            workspace: Workspace path
            analysis_result: AnalysisResult object from conversation analyzer
            terminal_data: Parsed terminal recording data
            llm_analysis: LLM analysis dictionary
            
        Returns:
            List of ProjectUpdate objects
        """
        updates = []
        current_tasks = self.load_current_tasks()

        workspace_name = workspace.name if workspace else "unknown"
        matching_project = self._find_matching_project(workspace_name, current_tasks)

        if not matching_project:
            return updates

        project_name = matching_project['name']
        evidence = []
        confidence = "low"

        if llm_analysis:
            evidence.extend(self._extract_evidence_from_llm(llm_analysis))

        if terminal_data:
            evidence.extend(self._extract_evidence_from_terminal(terminal_data))

        if analysis_result:
            evidence.extend(self._extract_evidence_from_analysis(analysis_result))

        if not evidence:
            return updates

        confidence = self._calculate_confidence(evidence)

        proposed_changes = self._generate_proposed_changes(
            matching_project,
            evidence,
            llm_analysis
        )

        if proposed_changes:
            reasoning = self._generate_reasoning(evidence, confidence)

            update = ProjectUpdate(
                session_id=session_id,
                session_date=datetime.now().strftime("%Y-%m-%d"),
                project_name=project_name,
                confidence=confidence,
                proposed_changes=proposed_changes,
                reasoning=reasoning,
                evidence=evidence[:10]
            )

            updates.append(update)

        return updates

    def save_pending_update(self, update: ProjectUpdate) -> Path:
        """
        Save pending update to file.

        Args:
            update: ProjectUpdate object

        Returns:
            Path to saved file
        """
        filename = f"{update.session_id}_{update.project_name}.json"
        filepath = self.pending_updates_path / filename

        with open(filepath, 'w') as f:
            f.write(update.to_json())

        return filepath

    def _find_matching_project(
        self,
        workspace_name: str,
        current_tasks: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Find project matching workspace name."""
        for project in current_tasks.get('active', []):
            if project['name'] == workspace_name:
                return project

        for project in current_tasks.get('recently_completed', []):
            if project['name'] == workspace_name:
                return project

        return None

    def _extract_evidence_from_llm(self, llm_analysis: Dict) -> List[str]:
        """Extract evidence from LLM analysis."""
        evidence = []

        for decision in llm_analysis.get('decisions', []):
            if any(re.search(pattern, decision.lower()) for pattern in self.COMPLETION_KEYWORDS):
                evidence.append(f"Decision: {decision[:100]}")

        for pattern in llm_analysis.get('patterns', []):
            if any(re.search(kw, pattern.lower()) for kw in self.PROGRESS_KEYWORDS):
                evidence.append(f"Pattern: {pattern[:100]}")

        summary = llm_analysis.get('summary', '')
        if summary and any(re.search(pattern, summary.lower()) for pattern in self.COMPLETION_KEYWORDS):
            evidence.append(f"Summary indicates completion: {summary[:100]}")

        return evidence

    def _extract_evidence_from_terminal(self, terminal_data: Dict) -> List[str]:
        """Extract evidence from terminal recording."""
        evidence = []
        text = terminal_data.get('raw_text', '')

        if 'test' in text.lower() and ('pass' in text.lower() or 'ok' in text.lower()):
            evidence.append("Tests passed in terminal")

        if re.search(r'git commit', text, re.IGNORECASE):
            commits = re.findall(r'git commit.*?(?:\n|$)', text, re.IGNORECASE)
            if commits:
                evidence.append(f"Git commits: {len(commits)} commit(s)")

        if re.search(r'(deployed|merged|pushed)', text, re.IGNORECASE):
            evidence.append("Deployment/merge activity detected")

        return evidence

    def _extract_evidence_from_analysis(self, analysis_result: Any) -> List[str]:
        """Extract evidence from AnalysisResult object."""
        evidence = []

        if hasattr(analysis_result, 'decisions'):
            for decision in analysis_result.decisions:
                if any(re.search(pattern, decision.lower()) for pattern in self.COMPLETION_KEYWORDS):
                    evidence.append(f"Decision: {decision[:100]}")

        if hasattr(analysis_result, 'todos'):
            completed_todos = [t for t in analysis_result.todos if 'complete' in t.lower() or 'done' in t.lower()]
            if completed_todos:
                evidence.append(f"Completed todos: {len(completed_todos)}")

        return evidence

    def _calculate_confidence(self, evidence: List[str]) -> str:
        """Calculate confidence level based on evidence."""
        if len(evidence) >= 5:
            return "high"
        elif len(evidence) >= 3:
            return "medium"
        else:
            return "low"

    def _generate_proposed_changes(
        self,
        current_project: Dict[str, Any],
        evidence: List[str],
        llm_analysis: Optional[Dict]
    ) -> Dict[str, Optional[str]]:
        """Generate proposed changes based on evidence."""
        changes = {}

        has_completion = any(
            any(re.search(pattern, e.lower()) for pattern in self.COMPLETION_KEYWORDS)
            for e in evidence
        )

        if has_completion:
            current_status = current_project.get('status', '')
            if 'complete' not in current_status.lower():
                changes['status'] = f"{current_status} ✅"

        if llm_analysis and llm_analysis.get('summary'):
            summary = llm_analysis['summary']
            if len(summary) > 50:
                changes['recent_progress'] = summary[:500]

        return changes

    def _generate_reasoning(self, evidence: List[str], confidence: str) -> str:
        """Generate reasoning explanation."""
        reasoning_parts = [
            f"Detected {len(evidence)} pieces of evidence suggesting project state change.",
            f"Confidence level: {confidence}."
        ]

        if any('complete' in e.lower() for e in evidence):
            reasoning_parts.append("Evidence suggests phase or task completion.")

        if any('test' in e.lower() for e in evidence):
            reasoning_parts.append("Test results indicate progress.")

        if any('commit' in e.lower() for e in evidence):
            reasoning_parts.append("Git activity detected.")

        return " ".join(reasoning_parts)


def create_analyzer(cerebrum_path: Path) -> ProjectStateAnalyzer:
    """
    Factory function to create analyzer.

    Args:
        cerebrum_path: Path to cerebrum root

    Returns:
        ProjectStateAnalyzer instance
    """
    return ProjectStateAnalyzer(cerebrum_path)
