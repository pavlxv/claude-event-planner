---
name: artifact-validator
description: Structural and citation check for /plan-event Markdown artifacts (requirements, venue, live-events, weather, catering, logistics, budget, validation, schedule). Use after writing any artifact and before dependent work starts.
---

# Artifact validator

Every workflow artifact is a human-readable Markdown file with the **same skeleton**, so
humans and agents can read any of them the same way and the check below is deterministic.

## Required skeleton

```markdown
# <Title>

- Artifact: <type>            # requirements | venue | live-events | weather | catering | logistics | budget | validation | schedule
- Owner: <agent-name>
- Run: <run-id>
- Revision: <n>               # 1 on first write, +1 on every retry/revision

## Summary
2–5 sentences a person can read in 20 seconds.

## Details
Type-specific content (see below).

## Costs
| Item | Qty | Unit price | Total | Currency | Source |
|------|-----|-----------:|------:|----------|--------|
(omit the whole section only for requirements, weather, validation)

## Sources
- [Page title](https://…) — what it supports

## Open issues
- None   ← or a bullet per unresolved point
```

Rules checked by `scripts/check_artifact.py`:
1. Title line, the four metadata bullets, and the headings above in this order.
2. `Artifact:` matches the file name.
3. `## Sources` has ≥1 `http(s)` link — except `requirements` and `validation`.
4. Every `## Costs` row has numeric Qty/Unit price/Total, `Qty × Unit price = Total` (±0.01),
   a 3-letter currency, and a URL in Source (budget and schedule rows may cite the artifact type they come from, e.g. `venue`).
5. Type-specific required subsections in `## Details`:
   - requirements: `### Confirmed requirements`, `### Execution hints`, `### Open questions`
   - venue: `### Top 3 candidates`
   - live-events: `### Top 3 candidates`, `### Date conflicts`
   - weather: `### Outlook`, `### Risk assessment`
   - catering: `### Top 3 candidates`, `### Dietary coverage`
   - logistics: `### Transport`, `### Top 3 candidates` (accommodation)
   - budget: `### Totals`
   - validation: `### Gate results`
   - schedule: `### Program`, `### Options per slot` (generated from plan.json)
6. **Shortlists** (venue, live-events, catering, logistics): `### Top 3 candidates` holds
   exactly three blocks — fewer only with a `Shortlist note:` line saying why:

   ```markdown
   #### 1. Loft Example
   - Website: https://loft.example
   - Book: https://loft.example/contact | +48 22 000 00 00 | events@loft.example
   - Address: ul. Długa 1, 00-001 Warszawa
   - Price: 4000 PLN (room hire, 6 hours)
   - Fits because: 60 seated, step-free, projector included
   - Source: https://loft.example/events
   ```
   `Book` needs at least one booking URL, phone number or e-mail. Nothing is ever booked
   by the workflow — these are the contacts the user uses to book.
   Options dropped (time box, failed checks) go in an optional `### Declined options` list.

## How to run

```bash
python3 .claude/skills/artifact-validator/scripts/check_artifact.py runs/<run-id>/artifacts/venue.md
python3 .claude/skills/artifact-validator/scripts/check_artifact.py runs/<run-id>/artifacts/   # all
```
Exit code 0 = pass. Otherwise every finding is printed as `FAIL <rule>: <detail>`;
fix them in the owning agent and write the artifact again (bump `Revision`).
The PostToolUse hook runs this automatically on every artifact write.
