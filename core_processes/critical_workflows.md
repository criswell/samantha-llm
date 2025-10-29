# Critical Workflows

This file contains essential workflows, procedures, and "always do this" reminders that should be surfaced during bootstrap and when working on specific projects. These represent lessons learned the hard way and help prevent repeated mistakes.

---

## Universal Workflows (Apply to All Projects)

### Before Committing Code

- [ ] Run relevant tests locally
- [ ] Run linters/formatters
- [ ] Review your own changes (git diff)
- [ ] Update documentation if needed
- [ ] Check for sensitive data (keys, tokens, passwords)

### When Debugging CI Failures

- [ ] Check if the issue can be reproduced locally first
- [ ] Review CI logs thoroughly before making changes
- [ ] Consider if the fix addresses root cause vs. symptom

---

## Project-Specific Workflows

### Pipefitter

#### Before Pushing Pipefitter Changes

**CRITICAL**: Always test `pipefitter generate` locally before pushing to CI.

**Why**: Pipefitter changes that break generation won't be caught until CI runs, wasting time and CI resources.

**How to Test Locally**:

```bash
# Option 1: Direct execution (fastest)
cd <target-project>  # e.g., data_example_project
pipefitter generate --trace
cat tmp/combined_config.yml

# Option 2: Docker (mimics CI exactly)
cd pipefitter
docker build . --build-arg nexus_key=$NEXUS_USER:$NEXUS_PASS -t pipefitter-local
cd ../<target-project>
docker run -v $(pwd):/workspace -w /workspace \
  -e PIPEFITTER_DOCKER=true \
  pipefitter-local \
  /opt/pipefitter/bin/pipefitter --trace generate
```

**Reference**: See `pipefitter/PIPEFITTER_LOCAL_TESTING.md` for full documentation.

**When to Use**:
- After modifying generators or templates
- After changing strategy logic
- When adding new job types or executors
- Before creating a pre-release

#### Pipefitter Development Workflow

1. Make changes to generators/templates/strategies
2. Run unit tests: `bundle exec rspec`
3. Test against real project locally (see above)
4. Verify generated config is valid
5. Run full test suite: `bundle exec rspec && bundle exec rubocop`
6. Commit and push
7. Create pre-release if testing in CI: Use `[UI] Pipefitter Prerelease` GitHub Action

---

## Memory Management Workflows

### When to Create Short-Term Memories

Create a memory file when:
- You discover a non-obvious workflow or procedure
- Important technical decisions are made
- You learn something that would save time if remembered
- A user provides important context about preferences/constraints
- You encounter and solve a tricky bug

### When to Escalate Memory Importance

Upgrade a memory to `importance: high` when:
- You reference it multiple times (3+ sessions)
- It prevents a costly mistake
- It's a critical workflow that should always be followed
- It contains foundational knowledge for a project

### When to Transfer to Long-Term Memory

Transfer from short-term to long-term when:
- Memory is older than 90 days and still relevant
- Memory has `importance: high` and contains foundational knowledge
- You reference it frequently across multiple sessions
- A project completes and its learnings should be preserved
- You notice a recurring pattern worth codifying

---

## Adding New Critical Workflows

When you discover a new critical workflow:

1. Add it to this file under the appropriate section
2. Create or update a short-term memory with `type: quick-reference`
3. If project-specific, also document in project's `*_WORKFLOWS.md` file
4. Update the short-term memory index

---

## Workflow Checklist Format

Use this format when adding new workflows:

```markdown
### [Workflow Name]

**CRITICAL/IMPORTANT/RECOMMENDED**: [One-line description]

**Why**: [Explanation of why this matters]

**How**: [Step-by-step instructions or code examples]

**Reference**: [Link to detailed documentation if available]

**When to Use**: [Specific triggers or conditions]
```
