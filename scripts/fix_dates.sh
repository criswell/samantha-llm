#!/bin/bash

# Fix dates in memory files to match actual file creation dates
# This is a one-time migration script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CEREBRUM_DIR="$(dirname "$SCRIPT_DIR")"
STM_DIR="${CEREBRUM_DIR}/short-term-memory/.ai"

echo "Fixing dates in memory files..."
echo "================================"

# Mapping of incorrect filename dates to correct dates based on file modification times
declare -A DATE_FIXES=(
    ["2025-01-28_autonomy_clarification.md"]="2025-10-28"
    ["2025-01-28_bootstrap_test.md"]="2025-10-28"
    ["2025-01-28_memory_system_improvements.md"]="2025-10-28"
    ["2025-01-29_critical_memory_flag_implementation.md"]="2025-10-29"
    ["2025-01-29_never_commit_to_master.md"]="2025-11-04"
    ["2025-01-29_offsite_presentation_prep.md"]="2025-10-30"
    ["2025-01-29_pipefitter_local_testing.md"]="2025-10-29"
    ["2025-10-29-phase3-workflow-generator.md"]="2025-10-29"
)

cd "$STM_DIR"

for old_filename in "${!DATE_FIXES[@]}"; do
    correct_date="${DATE_FIXES[$old_filename]}"
    
    if [ ! -f "$old_filename" ]; then
        echo "⚠️  Skipping $old_filename (not found)"
        continue
    fi
    
    # Extract description from old filename
    description=$(echo "$old_filename" | sed -E 's/^[0-9]{4}-[0-9]{2}-[0-9]{2}[-_]//' | sed 's/\.md$//')
    new_filename="${correct_date}_${description}.md"
    
    echo ""
    echo "Processing: $old_filename"
    echo "  → New filename: $new_filename"
    echo "  → New date: $correct_date"
    
    # Update date in YAML frontmatter
    sed -i "s/^date: .*/date: ${correct_date}/" "$old_filename"
    
    # Rename file if filename needs to change
    if [ "$old_filename" != "$new_filename" ]; then
        mv "$old_filename" "$new_filename"
        echo "  ✅ Renamed and updated"
    else
        echo "  ✅ Updated date in YAML"
    fi
done

echo ""
echo "================================"
echo "✅ Date fixes complete"
echo ""
echo "Next steps:"
echo "1. Run: .ai-cerebrum/scripts/validate_dates.sh"
echo "2. Update index.md if needed"
echo "3. Commit changes"
