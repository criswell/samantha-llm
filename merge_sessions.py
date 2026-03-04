#!/usr/bin/env python3
"""
Session merge process - consolidates completed sessions into cerebrum.

This script:
1. Finds completed session workspaces
2. Merges session guidance into main guidance file
3. Moves session memories to cerebrum
4. Archives processed sessions
"""

import sys
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Dict, Any

# Import session workspace
try:
    from session_workspace import SessionWorkspace, get_active_sessions
    HAS_WORKSPACE = True
except ImportError:
    HAS_WORKSPACE = False
    print("ERROR: session_workspace module not found")
    sys.exit(1)


def merge_guidance_files(cerebrum_path: Path, sessions: List[Tuple[SessionWorkspace, dict]]):
    """
    Merge session guidance files into main guidance file.

    Args:
        cerebrum_path: Path to cerebrum root
        sessions: List of (workspace, status) tuples for completed sessions
    """
    main_guidance_file = cerebrum_path / '.ai' / 'subconscious' / '.ai' / 'guidance.md'
    main_guidance_file.parent.mkdir(parents=True, exist_ok=True)

    # Read existing guidance or create new
    if main_guidance_file.exists():
        main_content = main_guidance_file.read_text()
    else:
        main_content = """---
last_updated: {timestamp}
---

# Subconscious Guidance

Quick orientation from recent sessions. For detailed analysis, see session workspaces.

## Recent Sessions

""".format(timestamp=datetime.now().isoformat())

    # Append each session's guidance
    session_entries = []
    for workspace, status in sorted(sessions, key=lambda x: x[1].get('completed_at', '')):
        if workspace.guidance_file.exists():
            guidance_content = workspace.guidance_file.read_text()

            # Extract just the session entry (skip headers)
            lines = guidance_content.split('\n')
            entry_lines = []
            in_sessions = False
            for line in lines:
                if '## Recent Sessions' in line:
                    in_sessions = True
                    continue
                if in_sessions and line.strip().startswith('- **'):
                    entry_lines.append(line)

            if entry_lines:
                session_entries.extend(entry_lines)

    # Add new entries to main guidance
    if session_entries:
        # Find the "## Recent Sessions" section
        lines = main_content.split('\n')
        insert_index = -1
        for i, line in enumerate(lines):
            if '## Recent Sessions' in line:
                insert_index = i + 1
                break

        if insert_index > 0:
            # Insert after "## Recent Sessions"
            lines = lines[:insert_index] + [''] + session_entries + lines[insert_index:]
            main_content = '\n'.join(lines)

    # Update timestamp
    main_content = main_content.replace(
        'last_updated: ',
        f'last_updated: {datetime.now().isoformat()} # '
    )

    main_guidance_file.write_text(main_content)
    print(f"✓ Merged {len(sessions)} session(s) into guidance.md")


def move_memories(cerebrum_path: Path, workspace: SessionWorkspace) -> int:
    """
    Move session memories to cerebrum short-term memory.

    Args:
        cerebrum_path: Path to cerebrum root
        workspace: SessionWorkspace instance

    Returns:
        Number of memories moved
    """
    dest_dir = cerebrum_path / '.ai' / 'short-term-memory' / '.ai'
    dest_dir.mkdir(parents=True, exist_ok=True)

    moved_count = 0
    if workspace.memories_dir.exists():
        for memory_file in workspace.memories_dir.glob('*.md'):
            dest_file = dest_dir / memory_file.name

            # Check for conflicts
            if dest_file.exists():
                # Rename with session ID
                stem = memory_file.stem
                dest_file = dest_dir / f"{stem}_{workspace.session_id}.md"

            shutil.copy2(memory_file, dest_file)
            moved_count += 1

    return moved_count


def archive_session(cerebrum_path: Path, workspace: SessionWorkspace):
    """
    Archive a processed session workspace.

    Args:
        cerebrum_path: Path to cerebrum root
        workspace: SessionWorkspace instance
    """
    archive_dir = cerebrum_path / '.ai' / 'subconscious' / '.ai' / 'processed' / workspace.session_id
    archive_dir.parent.mkdir(parents=True, exist_ok=True)

    # Move entire session workspace to archive
    shutil.move(str(workspace.root), str(archive_dir))


def merge_procedural_observations(cerebrum_path: Path, sessions: List[Tuple[SessionWorkspace, dict]]):
    """
    Merge procedural memory observations from completed sessions into runbooks.

    For each session's procedural observations:
    - If observations match an existing runbook domain: update that runbook's content
    - If observations suggest a new domain: create a draft runbook (confidence: low)
    - If corrections found: propagate to matching runbooks

    Args:
        cerebrum_path: Path to cerebrum root
        sessions: List of (workspace, status) tuples for completed sessions
    """
    procedural_dir = cerebrum_path / '.ai' / 'procedural-memory' / '.ai'
    index_file = procedural_dir / 'index.json'

    # Load existing index (or create empty)
    if index_file.exists():
        with open(index_file) as f:
            index = json.load(f)
    else:
        procedural_dir.mkdir(parents=True, exist_ok=True)
        index = {
            'last_updated': '',
            'description': 'Procedural memory registry.',
            'total_runbooks': 0,
            'runbooks': [],
            'loading_strategy': {
                'minimum_positive_categories': 2,
                'negative_signals_are_veto': True
            }
        }

    # Build domain lookup from existing runbooks
    domain_lookup = {}
    for rb in index.get('runbooks', []):
        domain_lookup[rb['domain']] = rb

    # Collect all observations from all sessions
    all_observations = []
    all_recommendations = []
    all_corrections = []

    for workspace, status in sessions:
        procedural_session_dir = workspace.procedural_dir
        if not procedural_session_dir.exists():
            continue

        for obs_file in procedural_session_dir.glob('procedural_*.json'):
            if obs_file.name.endswith('_raw.txt'):
                continue
            try:
                with open(obs_file) as f:
                    data = json.load(f)

                if not data.get('session_had_procedural_patterns', False):
                    continue

                all_observations.extend(data.get('observations', []))
                all_recommendations.extend(data.get('runbook_recommendations', []))
                all_corrections.extend(data.get('corrections_to_propagate', []))
            except (json.JSONDecodeError, KeyError) as e:
                print(f"  [WARN] Failed to read {obs_file}: {e}")

    if not all_observations and not all_recommendations and not all_corrections:
        print("  No procedural observations to merge")
        return

    print(f"  Found {len(all_observations)} observations, {len(all_recommendations)} recommendations, {len(all_corrections)} corrections")

    updated_domains = set()

    # Process corrections first (they modify existing runbooks)
    for correction in all_corrections:
        domain = correction.get('domain', '')
        if domain in domain_lookup:
            _apply_correction_to_runbook(procedural_dir, domain, correction)
            updated_domains.add(domain)
            print(f"  Applied correction to {domain}: {correction.get('wrong_assumption', '')[:60]}")

    # Process recommendations
    for rec in all_recommendations:
        domain = rec.get('domain', '')
        action = rec.get('action', 'create')

        if action == 'create' and domain not in domain_lookup:
            # Create new draft runbook
            _create_draft_runbook(procedural_dir, index, rec, all_observations)
            domain_lookup[domain] = index['runbooks'][-1]  # newly added
            updated_domains.add(domain)
            print(f"  Created draft runbook: {domain}")

        elif action == 'update' and domain in domain_lookup:
            _update_runbook_content(procedural_dir, domain, rec, all_observations)
            updated_domains.add(domain)
            print(f"  Updated runbook: {domain}")

        elif action == 'split' and domain in domain_lookup:
            # Splitting is complex — log it for manual review
            print(f"  [NOTE] Runbook split recommended for {domain}: {rec.get('reason', '')}")

    # Update observations into existing runbooks that weren't explicitly recommended
    for obs in all_observations:
        domain = obs.get('domain', '')
        if domain in domain_lookup and domain not in updated_domains:
            _merge_observation_signals(procedural_dir, index, domain, obs)
            updated_domains.add(domain)

    # Update index
    if updated_domains:
        index['last_updated'] = datetime.now().strftime('%Y-%m-%d')
        index['total_runbooks'] = len(index['runbooks'])
        with open(index_file, 'w') as f:
            json.dump(index, f, indent=2)
        print(f"  ✓ Updated procedural memory index ({len(updated_domains)} domains touched)")


def _apply_correction_to_runbook(procedural_dir: Path, domain: str, correction: Dict[str, Any]):
    """Apply a correction to an existing runbook's YAML frontmatter."""
    runbook_file = procedural_dir / f'{domain}.md'
    if not runbook_file.exists():
        return

    content = runbook_file.read_text()

    # Find the corrections section in YAML frontmatter and append
    correction_entry = (
        f"\n  - date: {datetime.now().strftime('%Y-%m-%d')}\n"
        f"    trigger: \"{correction.get('wrong_assumption', 'unknown')}\"\n"
        f"    wrong_interpretation: \"{correction.get('wrong_assumption', '')}\"\n"
        f"    correct_interpretation: \"{correction.get('correction', '')}\"\n"
        f"    action: \"{correction.get('trigger_impact', 'Added from subconscious analysis')}\""
    )

    # Try to append to existing corrections section
    if 'corrections:' in content:
        # Insert before the closing --- of frontmatter
        content = content.replace('corrections:', 'corrections:' + correction_entry, 1)
    else:
        # Add corrections section before closing ---
        parts = content.split('---\n', 2)
        if len(parts) >= 3:
            parts[1] = parts[1].rstrip() + f"\ncorrections:{correction_entry}\n"
            content = '---\n'.join(parts)

    # Add anti-signal from correction if specified
    trigger_impact = correction.get('trigger_impact', '')
    if trigger_impact and 'negative:' in content:
        anti_entry = (
            f"\n    - signal: \"{correction.get('wrong_assumption', '')}\"\n"
            f"      reason: \"{correction.get('correction', '')}\"\n"
            f"      added: {datetime.now().strftime('%Y-%m-%d')}"
        )
        content = content.replace('  negative:', '  negative:' + anti_entry, 1)

    # Update the updated date
    today = datetime.now().strftime('%Y-%m-%d')
    if 'updated:' in content:
        import re
        content = re.sub(r'updated: \d{4}-\d{2}-\d{2}', f'updated: {today}', content, count=1)

    runbook_file.write_text(content)


def _create_draft_runbook(procedural_dir: Path, index: Dict, recommendation: Dict, observations: list):
    """Create a new draft runbook from a recommendation."""
    domain = recommendation['domain']
    today = datetime.now().strftime('%Y-%m-%d')

    # Collect trigger signals from observations for this domain
    triggers = {'repo_signals': [], 'path_signals': [], 'keyword_signals': [], 'domain_signals': []}
    paths_seen = set()
    keywords_seen = set()

    for obs in observations:
        if obs.get('domain') == domain:
            suggested = obs.get('suggested_triggers', {})
            for category in triggers:
                for signal in suggested.get(category, []):
                    if signal not in triggers[category]:
                        triggers[category].append(signal)
            paths_seen.update(obs.get('paths_encountered', []))
            keywords_seen.update(obs.get('keywords', []))

    # Build negative signals
    anti_signals = recommendation.get('suggested_anti_signals', [])
    negative_yaml = ''
    for anti in anti_signals:
        negative_yaml += (
            f"\n    - signal: \"{anti.get('signal', '')}\"\n"
            f"      reason: \"{anti.get('reason', '')}\"\n"
            f"      added: {today}"
        )

    # Build key knowledge section
    key_knowledge = recommendation.get('key_knowledge', [])
    knowledge_lines = '\n'.join(f'- {k}' for k in key_knowledge) if key_knowledge else '- (Populated from session observations)'

    # Build paths table
    paths_table = ''
    for p in sorted(paths_seen):
        paths_table += f'| {p.split("/")[-1]} | `{p}` |\n'
    if not paths_table:
        paths_table = '| (auto-populated) | (from future sessions) |\n'

    content = f"""---
date: {today}
updated: {today}
domain: {domain}
topics: [{', '.join(keywords_seen) if keywords_seen else domain}]
type: runbook
confidence: low
triggers:
  positive:
    repo_signals: {json.dumps(triggers['repo_signals'])}
    path_signals: {json.dumps(triggers['path_signals'])}
    keyword_signals: {json.dumps(triggers['keyword_signals'])}
    domain_signals: {json.dumps(triggers['domain_signals'])}
  negative:{negative_yaml if negative_yaml else ' []'}
corrections: []
---

# {domain.replace('-', ' ').title()} Runbook

*Draft — auto-generated from subconscious analysis. Confidence: low.*
*Reason: {recommendation.get('reason', 'Procedural patterns detected')}*

## Project Locations

| Component | Path |
|-----------|------|
{paths_table}
## Key Architecture

{knowledge_lines}

## Common Operations

(To be populated from additional session observations)

## Critical Knowledge

(To be populated from corrections and repeated patterns)
"""

    runbook_file = procedural_dir / f'{domain}.md'
    runbook_file.write_text(content)

    # Add to index
    index_entry = {
        'file': f'{domain}.md',
        'domain': domain,
        'summary': recommendation.get('reason', f'Auto-generated runbook for {domain}'),
        'triggers': {
            'positive': triggers,
            'negative': [{'signal': a.get('signal', ''), 'reason': a.get('reason', '')} for a in anti_signals]
        },
        'confidence': 'low',
        'corrections_count': 0
    }
    index['runbooks'].append(index_entry)


def _update_runbook_content(procedural_dir: Path, domain: str, recommendation: Dict, observations: list):
    """Update an existing runbook with new knowledge from observations."""
    runbook_file = procedural_dir / f'{domain}.md'
    if not runbook_file.exists():
        return

    content = runbook_file.read_text()
    today = datetime.now().strftime('%Y-%m-%d')

    # Append new knowledge to the end of the file
    new_knowledge = recommendation.get('key_knowledge', [])
    if new_knowledge:
        update_section = f"\n\n## Update {today} (auto-generated)\n\n"
        for item in new_knowledge:
            update_section += f"- {item}\n"
        content += update_section

    # Update the updated date
    import re
    content = re.sub(r'updated: \d{4}-\d{2}-\d{2}', f'updated: {today}', content, count=1)

    runbook_file.write_text(content)


def _merge_observation_signals(procedural_dir: Path, index: Dict, domain: str, observation: Dict):
    """Merge trigger signals from an observation into an existing runbook's index entry."""
    for rb in index.get('runbooks', []):
        if rb['domain'] == domain:
            suggested = observation.get('suggested_triggers', {})
            existing = rb.get('triggers', {}).get('positive', {})

            for category in ['repo_signals', 'path_signals', 'keyword_signals', 'domain_signals']:
                existing_signals = existing.get(category, [])
                new_signals = suggested.get(category, [])
                for signal in new_signals:
                    if signal not in existing_signals:
                        existing_signals.append(signal)
                existing[category] = existing_signals

            rb['triggers']['positive'] = existing
            break


def merge_completed_sessions(cerebrum_path: Path, dry_run: bool = False):
    """
    Merge all completed sessions.

    Args:
        cerebrum_path: Path to cerebrum root
        dry_run: If True, show what would be done without doing it
    """
    # Find all completed sessions
    active_sessions = get_active_sessions(cerebrum_path)
    completed = [(ws, status) for ws, status in active_sessions if status['status'] == 'complete']

    if not completed:
        print("No completed sessions to merge")
        return

    print(f"\nFound {len(completed)} completed session(s) to merge:")
    for workspace, status in completed:
        completed_at = status.get('completed_at', 'unknown')
        print(f"  - {workspace.session_id} (completed: {completed_at})")

    if dry_run:
        print("\n[DRY RUN] Would merge these sessions but taking no action")
        return

    print("\nMerging sessions...")

    # Merge guidance files
    print("  1. Merging guidance files...", end='', flush=True)
    merge_guidance_files(cerebrum_path, completed)

    # Merge procedural memory observations
    print("  2. Merging procedural observations...")
    merge_procedural_observations(cerebrum_path, completed)

    # Move memories and archive each session
    total_memories = 0
    for workspace, status in completed:
        print(f"  3. Processing {workspace.session_id}...", end='', flush=True)

        # Move memories
        memory_count = move_memories(cerebrum_path, workspace)
        total_memories += memory_count

        # Archive session
        archive_session(cerebrum_path, workspace)

        print(f" ✓ ({memory_count} memories)")

    print(f"\n✓ Merge complete!")
    print(f"  - Sessions merged: {len(completed)}")
    print(f"  - Memories moved: {total_memories}")
    print(f"  - Archived to: .ai/subconscious/.ai/processed/")


def main():
    """Main entry point for session merging."""
    if len(sys.argv) < 2:
        print("Usage: python merge_sessions.py <cerebrum_path> [--dry-run]")
        print("\nMerge completed session workspaces into cerebrum.")
        print("\nOptions:")
        print("  --dry-run    Show what would be done without doing it")
        print("\nExample:")
        print("  python merge_sessions.py /path/to/cerebrum")
        sys.exit(1)

    cerebrum_path = Path(sys.argv[1])
    dry_run = '--dry-run' in sys.argv

    if not cerebrum_path.exists():
        print(f"ERROR: Cerebrum path not found: {cerebrum_path}")
        sys.exit(1)

    merge_completed_sessions(cerebrum_path, dry_run=dry_run)


if __name__ == '__main__':
    main()
