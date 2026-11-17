# Migration: Technical Writing Core Process (2026-11-17)

## What changed

A new core process file, `core_processes/technical_writing.md`, defines
Samantha's writing standard. It adapts ASD-STE100 Simplified Technical
English, scoped by audience:

- Session output for the user stays verbose (the working register,
  protected).
- Output written for other people (team docs, reports, PR bodies,
  wiki, Slack, runbooks) uses Simplified Technical English: short
  sentences, one fact per sentence, tables over compressed prose, with
  a hard rule that no fact, condition, or receipt is ever deleted to
  meet a word count.

Four files changed, plus one vendored tool:

1. `core_processes/technical_writing.md` (new): the standard.
2. `persona/main.md`: Section 4 gains "The Audience Rule" paragraph.
3. `core_processes/bootstrap.md`: Step 2 now reads the new file as
   item 3.
4. `migrations/README.md`: this guide is listed under Active
   Migrations.
5. `scripts/ste_lint.py` (vendored): the structural linter from
   danyuchn/asd-ste100-skill (MIT, Copyright (c) 2026 Dustin Yuchen
   Teng), with the license at `scripts/ste_lint.py.LICENSE`. The
   core process references it as the machine check. Verified on this
   box: selftest passes, a violation-rich sample yields 11 findings,
   a clean sample yields zero, and the core process file itself lints
   clean.

## Why

The user and Samantha are both verbose. That helps the two of them.
It produces walls of text that other people find hard to read. The
user asked for a core fix (2026-11-17), ahead of writing findings
reports for the team.

## What each instance must do

Nothing manual. Bootstrap Step 2 now includes the file. The next
bootstrap on each instance loads the standard and the persona rule.
Until then, instances that hear about this migration should read
`core_processes/technical_writing.md` in-session.

## Instance status

| Instance | Migrated | Notes |
| --- | --- | --- |
| Work laptop | yes | Live session 2026-11-17 wrote the migration; read the file in-session |
| Linux box (idaho) | pending | Next bootstrap |
| Windows PC (E:\work) | pending | Next bootstrap |

## Deletion criteria

Delete this guide when all three instances have bootstrapped after
2026-11-17. Record completion in the migrations README, then remove
this file.
