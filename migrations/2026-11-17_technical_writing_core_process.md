# Migration: Technical Writing Core Process (2026-11-17)

## What changed

A new core process file, `core_processes/technical_writing.md`, defines
Samantha's writing standard. It adapts ASD-STE100 Simplified Technical
English, scoped by audience:

- Session output for Sam stays verbose (the working register,
  protected).
- Output written for other people (team docs, reports, PR bodies,
  wiki, Slack, runbooks) uses Simplified Technical English: short
  sentences, one fact per sentence, tables over compressed prose, with
  a hard rule that no fact, condition, or receipt is ever deleted to
  meet a word count.

Three files changed:

1. `core_processes/technical_writing.md` (new): the standard.
2. `persona/main.md`: Section 4 gains "The Audience Rule" paragraph.
3. `core_processes/bootstrap.md`: Step 2 now reads the new file as
   item 3.

## Why

Sam and Samantha are both verbose. That helps the two of them. It
produces walls of text that other people find hard to read. Sam asked
for a core fix (2026-11-17) after reviewing the 6171 liveness audit,
ahead of writing findings reports for his team.

## What each instance must do

Nothing manual. Bootstrap Step 2 now includes the file. The next
bootstrap on each instance loads the standard and the persona rule.
Until then, instances that hear about this migration should read
`core_processes/technical_writing.md` in-session.

## Instance status

| Instance | Migrated | Notes |
| --- | --- | --- |
| Work laptop (doximity workspace) | yes | Live session 2026-11-17 wrote the migration; read the file in-session |
| Linux box (idaho) | pending | Next bootstrap |
| Windows PC (E:\work) | pending | Next bootstrap |

## Deletion criteria

Delete this guide when all three instances have bootstrapped after
2026-11-17. Record completion in the migrations README, then remove
this file.
