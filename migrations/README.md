# Cerebrum Migrations

This directory contains temporary migration guides for system updates that affect multiple Samantha Hartwell instances.

## Active Migrations

- **2025-12-03: JSON Index Format** (`2025-12-03_json_indexes.md`)
  - Status: Active
  - Migrating from markdown to JSON index format for token efficiency
  - Delete after all instances complete migration

## Completed Migrations

None yet.

## Guidelines

**When to create a migration guide:**
- Changes to core cerebrum structure (bootstrap, memory format, etc.)
- New required files or directories
- Breaking changes to existing workflows
- Updates that require manual action across instances

**Migration file naming:**
- Format: `YYYY-MM-DD_brief_description.md`
- Use lowercase with underscores
- Include completion date in filename

**Migration lifecycle:**
1. Create guide in this directory
2. Update bootstrap.md to check for migrations (if not already)
3. Track status in migration file (table of instances)
4. Delete guide after all instances migrate
5. Move to "Completed Migrations" section in this README (optional, for history)

**What to include:**
- Clear description of what changed and why
- Step-by-step migration instructions
- Schema/format references if applicable
- Status tracking table
- Deletion criteria

## Bootstrap Integration

The bootstrap process (Step 1) checks for `migrations/*.md` files and prompts reading them before proceeding. This ensures all instances see migration guides immediately.
