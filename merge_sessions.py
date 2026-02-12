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
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

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

    # Move memories and archive each session
    total_memories = 0
    for workspace, status in completed:
        print(f"  2. Processing {workspace.session_id}...", end='', flush=True)

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
