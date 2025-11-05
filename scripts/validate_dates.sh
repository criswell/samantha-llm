#!/bin/bash

# Validates dates in memory files
# Checks for:
# - Future dates
# - Mismatches between filename date and YAML frontmatter date
# - Missing date fields

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CEREBRUM_DIR="$(dirname "$SCRIPT_DIR")"

CURRENT_DATE=$(date +%Y-%m-%d)
CURRENT_TIMESTAMP=$(date +%s)

echo "Validating memory dates (current date: $CURRENT_DATE)"
echo "=================================================="

ERRORS=0

# Function to extract date from YAML frontmatter
extract_yaml_date() {
    local file="$1"
    grep "^date:" "$file" | head -1 | sed 's/date: *//' | tr -d '\r'
}

# Function to convert date to timestamp
date_to_timestamp() {
    local date_str="$1"
    date -d "$date_str" +%s 2>/dev/null || echo "0"
}

# Check short-term memory
echo ""
echo "Checking short-term memory..."
if [ -d "${CEREBRUM_DIR}/short-term-memory/.ai" ]; then
    for file in "${CEREBRUM_DIR}/short-term-memory/.ai"/*.md; do
        [ -f "$file" ] || continue
        [ "$(basename "$file")" = "index.md" ] && continue
        
        filename=$(basename "$file")
        
        # Extract date from filename (YYYY-MM-DD_description.md)
        filename_date=$(echo "$filename" | grep -oE '^[0-9]{4}-[0-9]{2}-[0-9]{2}')
        
        if [ -z "$filename_date" ]; then
            echo "  ❌ $filename: No date in filename"
            ((ERRORS++))
            continue
        fi
        
        # Extract date from YAML
        yaml_date=$(extract_yaml_date "$file")
        
        if [ -z "$yaml_date" ]; then
            echo "  ❌ $filename: Missing 'date:' field in YAML frontmatter"
            ((ERRORS++))
            continue
        fi
        
        # Check if dates match
        if [ "$filename_date" != "$yaml_date" ]; then
            echo "  ⚠️  $filename: Date mismatch (filename: $filename_date, YAML: $yaml_date)"
            ((ERRORS++))
        fi
        
        # Check if date is in the future
        file_timestamp=$(date_to_timestamp "$yaml_date")
        if [ "$file_timestamp" -gt "$CURRENT_TIMESTAMP" ]; then
            echo "  ❌ $filename: Future date detected ($yaml_date)"
            ((ERRORS++))
        fi
        
        # Check if date is too old for short-term memory (>90 days)
        days_old=$(( (CURRENT_TIMESTAMP - file_timestamp) / 86400 ))
        if [ "$days_old" -gt 90 ]; then
            echo "  ⚠️  $filename: Memory is $days_old days old (consider moving to long-term)"
        fi
    done
fi

# Check long-term memory
echo ""
echo "Checking long-term memory..."
if [ -d "${CEREBRUM_DIR}/long-term-memory/.ai" ]; then
    for file in "${CEREBRUM_DIR}/long-term-memory/.ai"/*.md; do
        [ -f "$file" ] || continue
        [ "$(basename "$file")" = "index.md" ] && continue
        
        filename=$(basename "$file")
        
        # Extract date from filename
        filename_date=$(echo "$filename" | grep -oE '^[0-9]{4}-[0-9]{2}-[0-9]{2}')
        
        if [ -z "$filename_date" ]; then
            echo "  ⚠️  $filename: No date in filename (acceptable for long-term)"
            continue
        fi
        
        # Extract date from YAML
        yaml_date=$(extract_yaml_date "$file")
        
        if [ -z "$yaml_date" ]; then
            echo "  ❌ $filename: Missing 'date:' field in YAML frontmatter"
            ((ERRORS++))
            continue
        fi
        
        # Check if dates match
        if [ "$filename_date" != "$yaml_date" ]; then
            echo "  ⚠️  $filename: Date mismatch (filename: $filename_date, YAML: $yaml_date)"
            ((ERRORS++))
        fi
        
        # Check if date is in the future
        file_timestamp=$(date_to_timestamp "$yaml_date")
        if [ "$file_timestamp" -gt "$CURRENT_TIMESTAMP" ]; then
            echo "  ❌ $filename: Future date detected ($yaml_date)"
            ((ERRORS++))
        fi
    done
fi

echo ""
echo "=================================================="
if [ $ERRORS -eq 0 ]; then
    echo "✅ All dates valid"
    exit 0
else
    echo "❌ Found $ERRORS issue(s)"
    exit 1
fi
