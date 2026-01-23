# Ralph Mode - Quick Reference

One-page guide for Ralph Mode activation and operation.

## Activation

**User says:** "Enter Ralph mode for [task]"

**You respond with:**
1. Task confirmation
2. Success criteria (machine-verifiable)
3. Token budget status
4. Guardrails loaded
5. Request confirmation to proceed

## Pre-Flight Checklist

- [ ] Task clearly defined
- [ ] Success criteria are machine-verifiable
- [ ] Guardrails loaded (general + project-specific)
- [ ] Token budget noted
- [ ] User confirmed criteria

## Iteration Loop

```
Work → Evaluate → Document → Decide → Monitor
  ↓        ↓          ↓         ↓         ↓
Code     Check      Update    Complete?  Tokens
Test     Criteria   Progress   Yes→Exit  OK→Loop
Run      Pass/Fail  Guardrails No→Work   High→Warn
```

## Iteration Communication Template

**Start:**
```
Iteration N: [what you'll work on]
Token usage: [X]% ([Zone])
```

**End:**
```
Iteration N complete:
✅ Completed: [list]
🔄 In progress: [list]
⏳ Remaining: [list]

Next: [iteration N+1 focus]
```

## Exit Conditions

| Condition | Trigger | Action |
|-----------|---------|--------|
| ✅ Success | All criteria met | Create memory, report completion |
| 🛑 User Stop | User says "stop" | Report progress, preserve state |
| ⚠️ Blocked | Need user decision | Pause, present options, await input |
| 🔄 Rotation | Tokens > 90% | Create memory, request fresh start |

## Token Zones

| Zone | Range | Action |
|------|-------|--------|
| 🟢 Green | < 60% | Continue normally |
| 🟡 Yellow | 60-80% | Focus on current work |
| 🔴 Red | 80-90% | Prepare for rotation |
| 🔥 Critical | > 90% | Force rotation NOW |

## Success Criteria Rules

**✅ GOOD (Machine-Verifiable):**
- "pytest passes"
- "mypy --strict succeeds"
- "benchmark < 100ms"
- "coverage >= 80%"

**❌ BAD (Subjective):**
- "code is clean"
- "performance is good"
- "tests are sufficient"
- "looks professional"

## Guardrails

**When to add:**
- Same mistake twice
- Tool behaves unexpectedly
- Discover project convention
- Test fails repeatedly

**Format:**
1. What failed
2. Why it failed
3. What to avoid
4. Correct approach
5. Code example

**Files:**
- `.ai-cerebrum/.ai/ralph-guardrails/general.md` - Universal
- `.ai-cerebrum/.ai/ralph-guardrails/[project].md` - Project-specific
- `.ai-cerebrum/.ai/ralph-guardrails/index.json` - Registry

## Memory Creation

**When:**
- Task > 3 iterations
- Discovered non-obvious solution
- Context rotation needed
- Task incomplete (for resumption)

**Include:**
- Task description & criteria
- What was accomplished
- Key decisions
- Challenges encountered
- Guardrails added
- How to resume

## Best Practices

1. **Start small** - First sessions should be simple tasks
2. **Clear criteria** - Spend time defining upfront
3. **Trust process** - Iteration and mistakes are expected
4. **Use git** - Commit after each iteration
5. **Monitor tokens** - Don't let it sneak up
6. **Read guardrails** - Avoid known pitfalls
7. **Document discoveries** - Add guardrails immediately
8. **Be concise** - Long explanations slow things down
9. **Verify everything** - Run tests, don't assume
10. **Human review** - Always review output before merging

## Common Problems

| Problem | Solution |
|---------|----------|
| Infinite loop | Refine criteria, check test flakiness |
| Goal drift | Restate criteria explicitly |
| Context explosion | Be more concise, rotate earlier |
| Unclear test failures | Run with `-v`, add debug output |

## Critical Reminders

- Ralph Mode respects **all critical memories**
- Ralph Mode follows **existing git workflow** (no direct commits to master)
- Ralph Mode is **opt-in**, never automatic
- **Human review required** before merging any output
- Token consumption can be significant - use for suitable tasks
- Security review is **mandatory** for all output

## File Locations

- **Documentation:** `.ai-cerebrum/core_processes/ralph_mode.md`
- **Guardrails:** `.ai-cerebrum/.ai/ralph-guardrails/`
- **Task Template:** `.ai-cerebrum/templates/ralph_task_template.md`
- **This Guide:** `.ai-cerebrum/templates/ralph_quick_reference.md`

## Activation Examples

**Simple task:**
```
User: "Enter Ralph mode to add type hints to config.py"
```

**Complex task:**
```
User: "Ralph mode: implement cache invalidation with test-driven development"
```

**Resume task:**
```
User: "Resume Ralph mode on type annotations task"
You: [Read memory from previous session, continue from last state]
```

## Exit Examples

**Success:**
```
Ralph Mode complete! ✅

All success criteria met:
✅ pytest passes (42 tests)
✅ mypy --strict succeeds
✅ coverage >= 80% (actual: 87%)

Files modified: 3
Iterations: 5
Duration: ~30 minutes

Exiting Ralph Mode. Ready for code review.
```

**User Stop:**
```
Stopping Ralph Mode as requested.

Progress:
✅ Completed: Type hints added to config.py
🔄 Partial: Type hints in generator.py (60%)
⏳ Remaining: block_registry.py, tests

State preserved in files and git.
Can resume with: "Resume Ralph mode on type annotations"
```

**Context Rotation:**
```
Context limit approaching - Rotating to fresh context.

Progress:
✅ Completed: [detailed list]
🔄 Current: [current state]
⏳ Remaining: [detailed checklist]

Memory created: .ai-cerebrum/.ai/short-term-memory/.ai/2026-01-23_ralph_type_annotations.md

To resume: "Resume Ralph mode on type annotations"
```

---

**Full Documentation:** See `.ai-cerebrum/core_processes/ralph_mode.md`
