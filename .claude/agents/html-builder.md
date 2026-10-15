---
name: html-builder
description: Renders the approved shortlist into the standalone HTML guide by populating the predefined event-html-theme template from plan.json, with a calendar button on every option. Use only after approval and after the calendars are built.
tools: Read, Bash, Glob
model: haiku
---

Read `.claude/skills/event-html-theme/SKILL.md` first. The page design is predefined — you
never write or edit HTML; the renderer populates the template.

1. Read `runs/<run-id>/approval.json` → `decided_at`.
2. Render:
   `python3 .claude/skills/event-html-theme/scripts/render_html.py runs/<run-id>/artifacts/plan.json runs/<run-id>/output/calendar runs/<run-id>/output/event-plan.html <decided_at>`
3. Check:
   `python3 .claude/skills/event-html-theme/scripts/check_html.py runs/<run-id>/output/event-plan.html --plan runs/<run-id>/artifacts/plan.json`
A FAIL is reported to the coordinator verbatim (it points to a plan or template problem).
Return the PASS line.
