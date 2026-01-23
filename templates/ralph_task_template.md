# Ralph Mode Task Template

Use this template to define tasks for Ralph Mode sessions. The more specific and measurable your success criteria, the more effective the iterative coding loop will be.

## Template

```markdown
# Ralph Mode Task: [Task Name]

**Created:** YYYY-MM-DD
**Project:** [project-name]
**Estimated Complexity:** [Low/Medium/High]

## Task Description

[Clear, concise description of what needs to be accomplished. Include context about why this task is needed and what problem it solves.]

## Success Criteria (Machine-Verifiable)

These must be objectively checkable. Use tests, linters, benchmarks, etc.

### Required Criteria
- [ ] [Criterion 1 - must be machine-checkable]
- [ ] [Criterion 2 - must be machine-checkable]
- [ ] [Criterion 3 - must be machine-checkable]

### Optional Criteria
- [ ] [Nice-to-have criterion 1]
- [ ] [Nice-to-have criterion 2]

## Verification Commands

List the exact commands to verify success criteria:

```bash
# Run tests
pytest tests/

# Check code formatting
black --check src/

# Check linting
ruff check src/

# Type checking
mypy src/

# Run benchmarks (if applicable)
pytest tests/benchmarks/ --benchmark-only

# Check coverage (if applicable)
pytest --cov=src --cov-report=term --cov-fail-under=80
```

## Manual Verification (Post-Ralph)

Items that require human judgment after Ralph Mode completes:

- [ ] Code review for clarity and maintainability
- [ ] Architecture aligns with project patterns
- [ ] Security considerations addressed
- [ ] Performance is acceptable
- [ ] Documentation is clear and helpful
- [ ] Changes don't introduce technical debt

## Files Expected to Change

List files that will likely be modified:

- `path/to/file1.py` - [expected changes]
- `path/to/file2.py` - [expected changes]
- `tests/test_*.py` - [expected test additions]

## Constraints and Guidelines

### Must Follow
- [Constraint 1 - e.g., "Don't modify the public API"]
- [Constraint 2 - e.g., "Maintain backward compatibility"]
- [Constraint 3 - e.g., "Follow existing code style"]

### Should Consider
- [Guideline 1 - e.g., "Prefer composition over inheritance"]
- [Guideline 2 - e.g., "Keep functions under 50 lines"]
- [Guideline 3 - e.g., "Add docstrings for public functions"]

## Related Context

### Documentation
- [Link to relevant design docs]
- [Link to API documentation]
- [Link to architectural decisions]

### Similar Work
- [Reference to similar implementation]
- [Previous PRs addressing related issues]

### Dependencies
- [Other tasks that must complete first]
- [External libraries or tools needed]

## Activation Command

When ready to start, say:

"Enter Ralph mode for [Task Name]"

or

"Ralph mode: [brief task description]"

## Notes

[Any additional context, gotchas, or considerations that don't fit above]
```

---

## Filled Example: Add Type Annotations to Config Module

```markdown
# Ralph Mode Task: Add Type Annotations to Config Module

**Created:** 2026-01-23
**Project:** bricklayer
**Estimated Complexity:** Medium

## Task Description

Add complete type annotations to the `src/bricklayer/config.py` module to enable static type checking with mypy. This module handles configuration loading and validation, and type hints will improve IDE support and catch configuration errors at development time.

## Success Criteria (Machine-Verifiable)

### Required Criteria
- [ ] All functions have complete type annotations (parameters and return types)
- [ ] All class attributes have type annotations
- [ ] mypy passes with `--strict` flag on config.py
- [ ] All existing tests still pass: `pytest tests/test_config.py`
- [ ] No new warnings or errors in CI

### Optional Criteria
- [ ] Add TypedDict for configuration dictionary structures
- [ ] Use Protocols for interface definitions where applicable

## Verification Commands

```bash
# Type checking (must pass)
mypy --strict src/bricklayer/config.py

# Run existing tests (must pass)
pytest tests/test_config.py -v

# Run full test suite (must pass)
pytest tests/

# Check formatting still good
black --check src/bricklayer/config.py

# Check linting
ruff check src/bricklayer/config.py
```

## Manual Verification (Post-Ralph)

- [ ] Type annotations improve code clarity
- [ ] No overuse of `Any` type (should be < 3 instances)
- [ ] Generic types used appropriately for containers
- [ ] IDE autocomplete works better with types
- [ ] Type stubs for external deps if needed

## Files Expected to Change

- `src/bricklayer/config.py` - Add all type annotations
- `tests/test_config.py` - Possibly add type-checking tests
- `src/bricklayer/types.py` - May create for shared type definitions

## Constraints and Guidelines

### Must Follow
- Don't change any function behavior
- Don't change the public API
- Maintain backward compatibility
- All existing tests must continue to pass unchanged

### Should Consider
- Use `from __future__ import annotations` for forward references
- Use `TYPE_CHECKING` guard for type-only imports (avoid circular imports)
- Prefer `Protocol` over `ABC` for structural typing
- Use `TypedDict` for complex dictionary structures
- Add `# type: ignore` with explanation only if absolutely necessary

## Related Context

### Documentation
- Python typing docs: https://docs.python.org/3/library/typing.html
- mypy cheat sheet: https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html

### Similar Work
- `src/bricklayer/generator.py` - Already has complete type annotations
- PR #123 - Added types to similar module

### Dependencies
- None - can proceed immediately
- mypy already in dev dependencies

## Activation Command

"Enter Ralph mode for adding type annotations to config module"

## Notes

- Config.py has some complex nested dictionaries - consider TypedDict
- There's one function with dynamic behavior that might need Union types
- Watch out for circular imports with generator.py - use TYPE_CHECKING if needed
```

---

## Example: Test-Driven Development Task

```markdown
# Ralph Mode Task: Implement Cache Invalidation Feature

**Created:** 2026-01-23
**Project:** bricklayer
**Estimated Complexity:** High

## Task Description

Implement intelligent cache invalidation for the bricklayer generation system. Currently, cache is never invalidated, leading to stale configs when building blocks change. Need to detect changes in building blocks and invalidate cache accordingly.

## Success Criteria (Machine-Verifiable)

### Required Criteria
- [ ] Tests for cache invalidation logic pass (write tests first)
- [ ] Cache invalidated when any building block file changes
- [ ] Cache preserved when only unrelated files change
- [ ] All existing tests still pass: `pytest tests/`
- [ ] Integration test with real project passes
- [ ] Performance: invalidation check < 50ms (benchmark test)

### Optional Criteria
- [ ] Cache invalidation logged at INFO level
- [ ] Metrics for cache hit/miss/invalidation rates

## Verification Commands

```bash
# Run new tests (write these first!)
pytest tests/test_cache_invalidation.py -v

# Run full test suite
pytest tests/

# Run integration tests
pytest tests/integration/test_full_generation.py

# Run benchmarks
pytest tests/benchmarks/test_cache_performance.py --benchmark-only

# Type checking
mypy src/bricklayer/

# Coverage check
pytest --cov=src/bricklayer --cov-report=term --cov-fail-under=85
```

## Manual Verification (Post-Ralph)

- [ ] Logic is clear and maintainable
- [ ] Edge cases handled appropriately
- [ ] Error messages are helpful
- [ ] Performance impact is minimal
- [ ] Implementation matches architectural patterns

## Files Expected to Change

- `tests/test_cache_invalidation.py` - NEW - write tests first
- `src/bricklayer/cache.py` - Add invalidation logic
- `src/bricklayer/block_registry.py` - Integrate cache invalidation
- `src/bricklayer/types.py` - May add types for cache metadata
- `tests/integration/test_full_generation.py` - Add invalidation test cases

## Constraints and Guidelines

### Must Follow
- Follow TDD: write tests before implementation
- Don't break existing cache behavior (backward compatible)
- Use file system watches or checksums (decide in iteration 1)
- Cache invalidation must be reliable (no false negatives)

### Should Consider
- Hash building block contents for change detection
- Store cache metadata with timestamps and hashes
- Consider using watchdog library for file monitoring
- Graceful degradation if invalidation fails (warn, regenerate)

## Related Context

### Documentation
- Cache system design: `.ai/CACHE_ARCHITECTURE.md`
- Building blocks structure: `.circleci/building_blocks/README.md`

### Similar Work
- Mortar has similar cache invalidation in its CI system
- Look at how `mortar up` detects template changes

### Dependencies
- May need to add `watchdog` library for file monitoring
- Building blocks must have stable paths

## Activation Command

"Enter Ralph mode for implementing cache invalidation feature"

## Notes

- This is TDD task - start with test writing iterations
- Building blocks are in `.circleci/building_blocks/` - watch this directory
- Consider using file checksums vs modification times (more reliable)
- Need to handle both local development and CI environments
- Cache location: `tmp/bricklayer-cache/`
```

---

## Quick Task Definition Checklist

Before entering Ralph Mode, ensure your task definition has:

- [ ] Clear, specific task description
- [ ] Machine-verifiable success criteria (tests, linters, benchmarks)
- [ ] Exact verification commands listed
- [ ] Files expected to change identified
- [ ] Constraints clearly stated
- [ ] Related context provided
- [ ] Activation command ready

If you're missing any of these, refine the task definition first. Clear upfront definition leads to faster, more successful Ralph Mode sessions.
