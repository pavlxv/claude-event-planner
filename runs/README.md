# Stored workflow runs

Each folder is one `/plan-event` run, committed as evidence for the assignment:

```
runs/<run-id>/
  input.md                 the original request
  workflow-state.json      persisted state: step status, retries, hashes, history
  timebox.json             options checked / declined per agent (2-minute time box)
  artifacts/*.md           agent outputs (requirements … schedule)
  artifacts/plan.json      structured shortlist the outputs are generated from
  approval.json            the human decision bound to the schedule hash
  approval-log.jsonl       every approve/reject decision (revision loop evidence)
  output/event-plan.html   final guide (a calendar button on every option)
  output/calendar/*.ics    program.ics + one tentative calendar per option
```

Planned demonstration runs (inputs in `samples/`):

| Run | Scenario | What it demonstrates |
|-----|----------|----------------------|
| 1 | Warsaw team meetup | optional agents skipped, dietary + accessibility gates |
| 2 | Berlin weekend | Ticketmaster country scope, logistics, budget-gate retry |
| 3 | Barcelona garden party | weather climatology, indoor-fallback gate, a rejected-then-approved revision, a resumed interruption |

Tip for run 3: stop Claude Code mid-run (Ctrl+C twice) after group 1, restart, and use
`/plan-event --resume <run-id>` so the history shows the recovery.
