# Event Planner — Agentic Workflow

This repository implements a hub-and-spoke agentic workflow that prepares an **event
shortlist** for a group event in a supported European country. The user invokes it with
`/plan-event <request>`; the slash command instantiates the **coordinator** (the main
Claude Code thread), which gathers requirements, plans the work, dynamically selects
subagents, runs quality gates, enforces human approval, and persists state for resume.

**Nothing is ever booked, reserved, ordered or paid.** For every part of the event
(venue, show, dinner, hotel night…) the workflow returns the **top 3 options** with their
website and booking contacts; the user decides and books. Every option also gets its own
tentative calendar file, so it can be added to a calendar before deciding.

Deliverables (in `runs/<run-id>/output/`):
- `event-plan.html` — standalone guide rendered from a **predefined template**;
  every option has an *Add to calendar* button (calendar embedded in the page)
- `calendar/program.ics` — one tentative event per part of the event, listing its options
- `calendar/<slot>-<rank>.ics` — one tentative event per option, with booking contacts

---

## 1. Roles

### Coordinator — `/plan-event` (`.claude/commands/plan-event.md`)
Orchestrates only and **never writes event content**. It creates/resumes the run
(`scripts/state.py`), asks clarifying questions, builds the execution plan, launches
subagents (parallel when independent), runs checks and gates, maps failures to owners for
targeted retries, waits for human approval, then launches the output builders.

### Subagents (`.claude/agents/`)

| # | Agent | Owns | Runs when | External sources |
|---|-------|------|-----------|------------------|
| 1 | `requirements-formalizer` | `requirements.md` | always | — |
| 2 | `venue-planner` | `venue.md` — top 3 venues | always | Ticketmaster MCP (venues), web |
| 3 | `live-events-scout` | `live-events.md` — top 3 shows | ticketed entertainment wanted, or date-clash check | Ticketmaster MCP (events) |
| 4 | `weather-planner` | `weather.md` | outdoor parts / transfers | Open-Meteo MCP |
| 5 | `catering-planner` | `catering.md` — top 3 caterers | food/drinks in scope | web |
| 6 | `logistics-planner` | `logistics.md` — transport + top 3 hotels | travelling guests or multi-day | web |
| 7 | `budget-aggregator` | `budget.md` — cheapest / top-pick / priciest | always | ECB rates if needed |
| 8 | `validator` | `validation.md` — gates G0–G10 | always | WebFetch of option links |
| 9 | `schedule-builder` (synthesis) | `plan.json` → `schedule.md` | always | validated artifacts only |
| 10 | `ics-builder` | `output/calendar/*.ics` | after approval | scripts only |
| 11 | `html-builder` | `output/event-plan.html` | after calendars | scripts only |

Every agent writes only its own artifact in `runs/<run-id>/artifacts/`.

---

## 2. Execution flow

```
requirements-formalizer ──(clarifying Q&A, user confirms)──▶
  [ venue-planner , live-events-scout* , weather-planner* ]   ← group 1, parallel
  → [ catering-planner* , logistics-planner* ]                ← group 2, parallel (need venue shortlist)
  → budget-aggregator
  → validator  (gates G0–G10; targeted retry on fail, max 3 per step)
  → schedule-builder  (plan.json + schedule.md)               ← synthesis
  → HUMAN APPROVAL of the shortlist (scripts/approve.py; reject → revise → re-approve)
  → ics-builder → html-builder                                ← outputs, script-generated
```
`*` = optional, selected from the confirmed requirements. The dependency graph lives in
`scripts/state.py` (`STEPS`); `python3 scripts/state.py next <run-id>` returns every step
that may run now — all of them are launched in one message (parallel).

---

## 3. Execution rules

1. **One run = one folder** `runs/<run-id>/`: `input.md`, `workflow-state.json`,
   `timebox.json`, `artifacts/`, `output/`, and (after human action) `approval.json`.
2. **Requirements must be confirmed** before group 1 (country, city, dates, guests, budget +
   currency, occasion are mandatory). Confirmed values go to state meta.
3. **Plan adaptation**: optional steps are enabled with `state.py plan <run> --enable …`
   from the requirements' execution hints; disabled steps are `skipped`.
4. **No booking**: agents only read public pages and APIs. They never submit forms, buy
   tickets, send messages or claim anything is booked/reserved (gate G10).
5. **Top 3 per shortlist**: exactly three ranked options, each with a website and at least
   one booking contact (booking URL, phone or e-mail). Fewer only with a written reason.
6. **Time box — 120 s per option**: research agents announce each option with
   `scripts/timebox.py start`. If an option takes longer than 120 s, the `timebox_guard`
   hook declines it (recorded in `timebox.json`) and blocks further calls until the agent
   moves to the next option from its long list. Declined options are listed in the artifact.
   Limit: `EVENT_PLANNER_TIMEBOX_SECONDS` in `.claude/settings.json`.
7. **Checks after every artifact**: the PostToolUse hook runs the structural check
   (`artifact-validator`) or the plan schema check (`plan-data`); failures go straight back
   to the agent, and the coordinator re-runs only that step if it still fails.
8. **Quality gates** in `validator`. A failing gate → `state.py fail <run> <owner> "<gate>: …"`:
   the owner is retried and **all downstream steps are invalidated** and regenerated.
   After 3 retries the step is `blocked`, dependents stop, the coordinator reports.
9. **Human approval** is valid only when `approval.json` says `approved` **and** its hashes
   equal the current `schedule.md` and `plan.json`. Claude can never write it (hook).
   A rejection is applied by invalidating the affected steps; approval is requested again.
10. **Country scope**: every Ticketmaster call uses the confirmed `countryCode` (hook).
11. **Deterministic output**: `plan.json` follows the plan-data schema; `schedule.md`,
    the calendars and the HTML are generated from it by scripts. Same plan → same files.
12. **Resume**: `/plan-event --resume <run-id>` — `done` steps are kept; interrupted or
    modified steps (and their dependents) are redone.

---

## 4. Quality gates (validator)

| Gate | Check | Owner on failure |
|------|-------|------------------|
| G0 | every artifact passes the structural check | file owner |
| G1 | cheapest combination + 10 % ≤ budget (top picks over = warning) | `budget` or most expensive part |
| G2 | every venue option: capacity ≥ guests | `venue` |
| G3 | every venue option meets accessibility / facility must-haves | `venue` |
| G4 | every dietary need covered by every catering option | `catering` |
| G5 | every option in the confirmed country | owner |
| G6 | every option inside the event dates | owner |
| G7 | every option's website and booking link reachable and relevant | owner |
| G8 | high weather risk → indoor fallback | `venue` |
| G9 | exactly 3 options per shortlist (or a written reason) | owner |
| G10 | website + booking contact on every option; nothing claims to be booked | owner |

Output checks after approval: `validate_ics.py --plan` (one calendar per option + program)
and `check_html.py --plan` (template sections, options match plan, no internal names,
no external resources).

---

## 5. Skills (`.claude/skills/`)

- **artifact-validator** — structure, citations, cost arithmetic, top-3 candidate blocks.
- **plan-data** — `plan.json` schema check, computed budget, `schedule.md` rendering.
- **ics-calendar** — builds `program.ics` + one tentative `.ics` per option; validates them.
- **event-html-theme** — predefined template + partials, `render_html.py` populates them,
  `check_html.py` verifies the result; `example/plan.example.json` for design previews.

## 6. Hooks (`.claude/settings.json` → `.claude/hooks/`)

PreToolUse
- `approval_guard.py` — no output before a valid approval; Claude can't approve.
- `country_scope_guard.py` — Ticketmaster `countryCode` must equal the confirmed country.
- `no_leak_guard.py` — no internal file/agent names in user-facing output.
- `timebox_guard.py` — 120 s per option for research agents; auto-declines and redirects.

PostToolUse
- `post_write_state.py` — records each artifact write in `workflow-state.json` and runs
  the matching deterministic check (exit 2 feeds failures back to Claude).

## 7. MCP servers (`.mcp.json`)
- **ticketmaster** — `@delorenj/mcp-server-ticketmaster` (`search_ticketmaster`; needs `TICKETMASTER_API_KEY`).
- **open-meteo** — `open-meteo-mcp-server` (forecast ≤16 days, climate archive beyond; no key).

## 8. The coordinator must never
write event content, `approval.json`, or anything in `output/`; book or contact anyone;
re-run a `done` step except through `state.py fail` / `invalidate`; continue past a
`blocked` step; or mention internal file names to the user.
