# Ralph Mode - Iterative Coding Loop

**Last Updated:** 2026-01-23

## Overview

Ralph Mode is an operational mode for intensive coding tasks that require iterative refinement and validation. Named after Ralph Wiggum from The Simpsons, it embodies the principle of "iteration > perfection" - continuously working, evaluating, and improving until objective success criteria are met.

**Key Principle:** State lives in files and git history, not in LLM context. When context fills, a fresh agent instance picks up where the last one left off.

## When to Use Ralph Mode

Ralph Mode excels at tasks with **machine-verifiable success criteria**:

### Ideal Tasks
- ✅ Test-driven development (TDD) workflows
- ✅ Code refactoring with existing test suites
- ✅ API implementations with integration tests
- ✅ Bug fixes with reproducible test cases
- ✅ Database migrations with validation
- ✅ Performance optimizations with benchmarks
- ✅ Linting/formatting corrections
- ✅ Type annotation additions with mypy validation

### Avoid For
- ❌ Subjective design decisions ("make it prettier")
- ❌ Unclear requirements without measurable outcomes
- ❌ Deep architectural planning requiring human judgment
- ❌ Tasks requiring extensive user interaction
- ❌ Exploratory research without clear deliverables

## Activation Pattern

Ralph Mode is **opt-in** and requires explicit user activation:

### Activation Phrases
User says one of:
- "Enter Ralph mode for [task]"
- "Start iterative coding on [task]"
- "Use Ralph loop to implement [feature]"
- "Ralph mode: [task description]"

### Pre-Activation Checklist

Before entering Ralph Mode, you MUST:

1. **Confirm task understanding** - Restate the task in your own words
2. **Define success criteria** - Create machine-verifiable completion checklist
3. **Load guardrails** - Read project-specific and general guardrails
4. **Check token budget** - Note current usage and set thresholds
5. **Get user confirmation** - Don't start iteration until user approves criteria

### Example Activation Flow

**User:** "Enter Ralph mode to add type annotations to the bricklayer module"

**You:**
```
Entering Ralph mode. Let me confirm success criteria:

## Task: Add Type Annotations to Bricklayer Module

### Success Criteria:
- [ ] All functions and methods have type hints
- [ ] mypy passes with --strict mode
- [ ] No changes to functionality (tests still pass)
- [ ] Type stubs created for external dependencies if needed
- [ ] Docstrings updated to reflect type information

### Manual Verification:
- [ ] Human review of type choices
- [ ] Type annotations aid understanding

Token budget: ~135k remaining (Green zone)
Guardrails loaded: bricklayer (2 entries), general (5 entries)

Ready to begin iteration 1. Confirm criteria or adjust?
```

**User:** "Confirmed, proceed"

**You:** [Enter iteration loop]

## The Iteration Cycle

Once activated, execute this loop until exit conditions are met:

### Iteration Structure

```
LOOP:
  1. WORK
     - Make code changes
     - Run tests/validation
     - Document what was done

  2. EVALUATE
     - Check against success criteria
     - Identify what's complete
     - Identify what remains

  3. DOCUMENT
     - Update progress tracking
     - Add guardrails if new failures discovered
     - Note learnings for future iterations

  4. DECIDE
     - All criteria met? → EXIT (success)
     - Blocked on user input? → PAUSE (await user)
     - Can continue? → ITERATE
     - Context limit? → ROTATE (create memory, request restart)

  5. MONITOR
     - Check token usage
     - Green (< 60%): Continue normally
     - Yellow (60-80%): Note approaching limit
     - Red (> 80%): Prepare for context rotation
     - Critical (> 90%): Force wrap-up
END LOOP
```

### Iteration Communication

**Start of each iteration:**
```
Iteration N: [Brief description of what you'll work on]
Token usage: [percentage] ([zone])
```

**End of each iteration:**
```
Iteration N complete:
✅ Completed: [list]
🔄 In progress: [list]
⏳ Remaining: [list]

Next: [what iteration N+1 will focus on]
```

**Example:**
```
Iteration 3: Adding type hints to generator.py
Token usage: 45% (Green)

[... work happens ...]

Iteration 3 complete:
✅ Completed:
  - generator.py fully typed
  - mypy passes on generator.py

🔄 In progress:
  - yaml_merger.py (50% typed)

⏳ Remaining:
  - block_registry.py
  - Tests in test_generator.py

Next: Complete yaml_merger.py typing
```

## Exit Conditions

Ralph Mode exits when one of these conditions is met:

### 1. Success Exit ✅
**Trigger:** All success criteria are met and verified

**You say:**
```
Ralph Mode complete! ✅

All success criteria met:
✅ [criterion 1]
✅ [criterion 2]
...

Summary of changes:
- [change 1]
- [change 2]
...

Files modified: [count]
Tests added/modified: [count]
Total iterations: [count]

Exiting Ralph Mode. Ready for next task or manual review.
```

### 2. User-Requested Stop 🛑
**Triggers:**
- User says "stop", "exit Ralph mode", "pause"
- User provides new instructions mid-iteration

**You say:**
```
Stopping Ralph Mode as requested.

Progress at stop:
✅ Completed: [list]
🔄 Partial: [list]
⏳ Remaining: [list]

State preserved in:
- Files: [list of modified files]
- Git: [current branch/commit]
- Memory: [memory file if created]

Can resume later or proceed with different task.
```

### 3. Critical Blocker ⚠️
**Triggers:**
- Require user decision on approach
- Cannot proceed without clarification
- Found security/architectural issue requiring discussion

**You say:**
```
Pausing Ralph Mode - User input required.

Current situation: [description of blocker]

Options:
1. [Option A and implications]
2. [Option B and implications]
3. [Option C and implications]

Progress so far:
✅ Completed: [list]
🔄 Blocked: [list]

Awaiting your decision to proceed.
```

### 4. Context Rotation 🔄
**Trigger:** Token usage > 90%

**You say:**
```
Context limit approaching - Rotating to fresh context.

Progress summary:
✅ Completed: [detailed list]
🔄 In progress: [current work state]
⏳ Remaining: [detailed checklist]

Created memory: [path to memory file]
Updated guardrails: [list of new entries]

Files modified:
- [file 1]: [summary of changes]
- [file 2]: [summary of changes]

To resume Ralph Mode in next session:
1. Bootstrap normally
2. Say: "Resume Ralph mode on [task]"
3. I'll read the memory and continue from this point

Ready for fresh session.
```

## Token Usage Monitoring

Monitor token consumption throughout Ralph Mode:

### Green Zone (< 60%)
- **Status:** Plenty of context available
- **Action:** Continue normally
- **Communication:** Note percentage in iteration headers

### Yellow Zone (60-80%)
- **Status:** Approaching limit
- **Action:** Focus on completing current sub-task before starting new one
- **Communication:** "Approaching context limit, focusing on wrapping up current work"

### Red Zone (> 80%)
- **Status:** Context rotation likely needed soon
- **Action:** Complete current iteration, document extensively
- **Communication:** "Context nearly full - will complete current iteration then rotate"

### Critical Zone (> 90%)
- **Status:** Must rotate now
- **Action:** Immediately create comprehensive memory and request rotation
- **Communication:** Force exit with detailed state documentation

### Token Calculation
Approximate current usage as:
- Messages exchanged * ~1000 tokens/message
- Or use the token count provided by system
- Always err on side of caution

## Guardrails System

Guardrails are persistent learnings that prevent repeated mistakes across Ralph Mode sessions.

### Directory Structure
```
.ai-cerebrum/.ai/ralph-guardrails/
├── index.json          # Registry of all guardrails
├── general.md          # Cross-project patterns
└── [project-name].md   # Project-specific guardrails
```

### When to Add Guardrails

Add a guardrail when:
- A test fails repeatedly for the same reason
- You make the same mistake twice
- You discover a pattern that should be avoided
- A tool/command produces unexpected results
- You find a project-specific convention

### Guardrail Format

Each guardrail entry should contain:

```markdown
## [Short descriptive title]

**Date Added:** YYYY-MM-DD
**Context:** [What task/iteration this came from]

### What Failed
[Description of what went wrong]

### Why It Failed
[Root cause analysis]

### What to Avoid
- [Specific action/pattern to avoid]
- [Another thing to avoid]

### Correct Approach
[What to do instead]

**Example:**
```python
# ❌ DON'T
[bad code example]

# ✅ DO
[good code example]
```
```

### Reading Guardrails

At Ralph Mode activation:
1. Read `.ai-cerebrum/.ai/ralph-guardrails/index.json`
2. Load general guardrails from `general.md`
3. Load project-specific guardrails from `[current-project].md`
4. Keep them in mind throughout iterations
5. Explicitly reference them if about to violate one

During iterations:
- Check guardrails before taking actions that previously failed
- Reference specific guardrail if preventing a mistake: "Not doing X (guardrail #3)"

### Example Guardrail

```markdown
## Don't Use pip in Doximity Projects

**Date Added:** 2026-01-22
**Context:** Bricklayer Docker image implementation

### What Failed
Used `pip install` in Dockerfile, but data team standard is `uv`

### Why It Failed
Wasn't aware of data team standardization on uv package manager

### What to Avoid
- Using `pip install` for Python packages
- Using `python -m venv` for virtual environments

### Correct Approach
Always use `uv`:

```python
# ❌ DON'T
RUN pip install package-name

# ✅ DO
RUN uv pip install --system package-name
```

Exceptions: Only use pip to install uv itself
```

## Success Criteria Definition

Success criteria MUST be machine-verifiable. Here's how to define them:

### Template

```markdown
## Task: [Clear, concise task description]

### Machine-Verifiable Criteria
- [ ] All unit tests pass: `pytest tests/`
- [ ] Integration tests pass: `pytest tests/integration/`
- [ ] Linting passes: `ruff check .`
- [ ] Formatting passes: `black --check .`
- [ ] Type checking passes: `mypy src/`
- [ ] No security issues: `bandit -r src/`
- [ ] Documentation builds: `make docs`
- [ ] Coverage maintained: `pytest --cov --cov-fail-under=80`

### Manual Verification (Post-Ralph)
- [ ] Code review by human
- [ ] Architecture makes sense
- [ ] Performance acceptable
- [ ] Security considerations addressed
```

### Examples of Good vs Bad Criteria

**❌ BAD (Subjective):**
- "Code is clean and readable"
- "Performance is good"
- "Tests are comprehensive"
- "Documentation is clear"

**✅ GOOD (Objective):**
- "Black passes with --check flag"
- "Response time < 100ms (measured via benchmark)"
- "Coverage >= 80% (pytest --cov-fail-under=80)"
- "All docstrings present (pydocstyle)"

## Memory Management in Ralph Mode

Ralph Mode generates significant context. Manage it carefully:

### During Ralph Mode

**Don't create memories mid-iteration** unless:
- Discovering something that would be useful beyond this task
- Finding a pattern that should be a guardrail
- Context rotation is imminent

**Do create progress markers:**
- Update files with clear comments about state
- Use git commits to mark iteration boundaries
- Maintain a `RALPH_PROGRESS.md` file in project .ai/ directory

### On Ralph Mode Exit

**Always create a memory** if:
- Task spanned multiple iterations (> 3)
- Discovered non-obvious solutions
- Encountered significant challenges
- Context rotation occurred
- Task is incomplete (for resumption)

**Memory should include:**
- Task description and success criteria
- What was accomplished
- Key decisions made
- Challenges encountered
- Guardrails added
- How to resume if incomplete

### Example Memory Structure

```markdown
---
date: 2026-01-23
topics: [ralph-mode, bricklayer, type-annotations, iteration]
importance: medium
type: technical
project: dynamic-mortar-ci
---

# Ralph Mode Session: Type Annotations for Bricklayer

## Task
Add complete type annotations to bricklayer module with mypy --strict validation

## Iterations
Total: 7 iterations over 45 minutes

## Success Criteria (All Met ✅)
- [x] All functions typed
- [x] mypy --strict passes
- [x] Tests still pass
- [x] Type stubs for dependencies

## Key Decisions
1. Used Protocol for abstract interfaces (more Pythonic than ABCs)
2. Added TypedDict for configuration dictionaries
3. Used generics for container types

## Challenges
- Iteration 3: mypy complained about Union[str, Path] - solved with os.fspath()
- Iteration 5: Circular import for type hints - solved with TYPE_CHECKING guard

## Guardrails Added
- "Use TYPE_CHECKING for forward references" (bricklayer.md #4)

## Files Modified
- src/bricklayer/generator.py
- src/bricklayer/config.py
- src/bricklayer/types.py (new)
- tests/test_types.py (new)

## Outcome
✅ Complete - All type annotations added, mypy passes, tests pass
```

## Ralph Mode Best Practices

### 1. Start Small
For your first Ralph Mode sessions, choose small, well-defined tasks:
- Add type hints to a single module
- Fix linting errors in a directory
- Write tests for uncovered functions

### 2. Clear Success Criteria
Spend time upfront defining criteria. Vague criteria lead to infinite loops.

### 3. Trust the Process
Ralph Mode will make mistakes and iterate. That's the point. Don't intervene unless:
- Truly blocked
- Going in wrong direction
- Context limit approaching

### 4. Use Git Liberally
Commit after each iteration or logical chunk. This provides rollback points and clear progress markers.

### 5. Monitor Token Usage
Check periodically. Don't let it sneak up to critical zone without preparation.

### 6. Review Guardrails First
Before starting iteration, skim guardrails to avoid known pitfalls.

### 7. Document Discoveries
When you find something non-obvious, add a guardrail immediately. Don't wait until end.

### 8. Keep Prompts Simple
In iteration communication, be concise. "less is more" - long explanations slow things down.

### 9. Machine-Verify Everything
Don't assume tests pass - run them. Don't assume linting passes - check it. Trust but verify.

### 10. Human Review Required
Ralph Mode is not a substitute for code review. All output needs human verification before merging.

## Troubleshooting

### Problem: Infinite Loop
**Symptom:** Same iteration repeating without progress
**Solution:**
1. Check if success criteria are actually achievable
2. Check if tests are flaky
3. Add specific guardrail about the failure pattern
4. Exit and refine criteria with user

### Problem: Goal Drift
**Symptom:** Agent starts working on tangential issues
**Solution:**
1. Explicitly restate success criteria in next iteration
2. "Focusing only on: [original criteria]"
3. If drift continues, exit and reset

### Problem: Context Explosion
**Symptom:** Approaching token limit too quickly
**Solution:**
1. Make smaller atomic commits
2. Be more concise in iteration communication
3. Don't copy full error messages if pattern is clear
4. Rotate context earlier (70-80% instead of 90%)

### Problem: Test Failures Not Understood
**Symptom:** Tests fail but unclear why
**Solution:**
1. Run tests with `-v` or `-vv` for verbose output
2. Add debugging print statements
3. Run single test in isolation
4. If still unclear, pause and ask user

## Integration with Existing Workflows

Ralph Mode complements existing Samantha workflows:

### Relationship to Critical Memories
Critical memories are **always active**, including during Ralph Mode. If a critical memory says "always use uv", Ralph Mode respects that.

### Relationship to Project Documentation
Ralph Mode reads project `.ai/` documentation for context but doesn't modify it during iterations. Documentation updates happen post-Ralph in normal mode.

### Relationship to Git Workflow
Ralph Mode respects existing git rules:
- Never commit directly to master
- Work on feature branches
- User controls git push operations
- Create commits but let user handle PRs

### Relationship to Memory System
Ralph Mode is a **working mode**, not a separate persona. Memories created during/after Ralph sessions go in the standard memory system with `ralph-mode` topic tag.

## Advanced Patterns

### Pattern: Incremental Refactoring
For large refactoring tasks, use multiple Ralph sessions:
1. Session 1: Extract functions
2. Session 2: Add type hints
3. Session 3: Optimize performance
4. Session 4: Add comprehensive tests

Each session has clear, focused criteria.

### Pattern: Test-Driven Ralph
Structure Ralph sessions around TDD:
1. Iteration 1: Write failing tests
2. Iteration 2-N: Implement until tests pass
3. Iteration N+1: Refactor while keeping tests green

### Pattern: Progressive Enhancement
Start with minimal working version, then enhance:
1. Session 1: Basic functionality (tests pass)
2. Session 2: Error handling (edge case tests pass)
3. Session 3: Performance (benchmarks meet targets)
4. Session 4: Documentation (docstrings complete)

### Pattern: Parallel Ralph Sessions
Multiple related tasks can run in separate Ralph sessions:
- Developer: "Start Ralph mode on API implementation"
- Wait for completion
- Developer: "Start Ralph mode on API tests"
Each session has focused criteria.

## Limitations and Considerations

### What Ralph Mode Is Not
- **Not autonomous** - Requires explicit activation and user-defined criteria
- **Not unsupervised** - User should monitor progress and review output
- **Not a silver bullet** - Only works for suitable tasks with clear criteria
- **Not a replacement for human judgment** - Architecture and design still need human input

### Cost Considerations
Ralph Mode can consume significant tokens through iteration. Use it when:
- The task would take significant human time
- The criteria are clear and verifiable
- The economics favor compute over human hours

### Security Considerations
**Always review Ralph Mode output** before:
- Committing to main branches
- Deploying to production
- Sharing publicly
- Running with elevated privileges

Ralph Mode can introduce security issues through iteration. Human security review is mandatory.

## Quick Reference Card

**Activation:** User says "Enter Ralph mode for [task]"

**Pre-flight:**
1. Define success criteria
2. Load guardrails
3. Check token budget
4. Get user confirmation

**Iteration Loop:**
Work → Evaluate → Document → Decide → Monitor

**Exit Conditions:**
- ✅ Success (all criteria met)
- 🛑 User stop request
- ⚠️ Critical blocker
- 🔄 Context rotation (> 90% tokens)

**Token Zones:**
- Green (< 60%): Continue
- Yellow (60-80%): Focus
- Red (> 80%): Prepare rotation
- Critical (> 90%): Force rotation

**Guardrails:** Read at start, reference during work, add when discovering patterns

**Memory:** Create on exit if > 3 iterations or significant findings

---

**Related Files:**
- `.ai-cerebrum/core_processes/bootstrap.md` - Bootstrap process
- `.ai-cerebrum/core_processes/memory_management.md` - Memory system
- `.ai-cerebrum/.ai/ralph-guardrails/` - Guardrails directory
