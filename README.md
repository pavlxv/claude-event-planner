# Event Planner — reliable agentic workflow for Claude Code

`/plan-event` prepares a **shortlist** for a group event in a European country: for every
part of the event (venue, show, dinner, hotel…) the **top 3 options** with website and
booking contacts, plus weather and a budget range. **Nothing is booked** — you choose and
book. Output: a standalone **HTML guide** rendered from a predefined template, a program
calendar, and a **tentative .ics per option** (also one click away inside the guide).

A coordinator selects subagents dynamically, runs them in parallel where possible,
time-boxes each option to 2 minutes, checks quality gates with targeted retries, persists
state for resume, and only builds the output after a **human approval verified by hash**.

Workflow design and execution rules: see [`CLAUDE.md`](CLAUDE.md).

## Repository layout

```
CLAUDE.md                       workflow documentation and rules (loaded by Claude Code)
.mcp.json                       MCP servers: Ticketmaster, Open-Meteo
.claude/
  commands/plan-event.md        /plan-event — the coordinator
  agents/*.md                   11 subagents
  skills/artifact-validator/    structural + citation check, top-3 candidate blocks
  skills/plan-data/             plan.json schema, computed budget, schedule.md renderer
  skills/ics-calendar/          program + per-option RFC 5545 calendars, validator
  skills/event-html-theme/      predefined template + partials, renderer, HTML check
  hooks/*.py                    PreToolUse / PostToolUse hooks
  settings.json                 hook registration, permissions, MCP enablement
scripts/state.py                persisted workflow state machine (plan / next / fail / resume)
scripts/approve.py              the ONLY way to approve/reject — run by the human
scripts/timebox.py              per-option 2-minute time box used by research agents
samples/                        3 sample requests
runs/                           stored runs (inputs, artifacts, state, outputs)
```

## Prerequisites

| Tool | Version | Why |
|------|---------|-----|
| [Claude Code](https://docs.claude.com/en/docs/claude-code) | recent | runs the workflow |
| Node.js + npx | 18+ | starts both MCP servers |
| Python | 3.9+ (stdlib only) | hooks, state, validators |
| Ticketmaster API key | free | venue/event search |

Open-Meteo needs no key.

## Setup (clean checkout)

```bash
git clone <this-repo> event-planner && cd event-planner
cp .env.example .env            # then paste your key into .env
set -a; source .env; set +a     # export TICKETMASTER_API_KEY for this shell
chmod +x scripts/*.py .claude/hooks/*.py
claude                          # start Claude Code in the repo root
```
Inside Claude Code:
- run `/mcp` — `ticketmaster` and `open-meteo` should be **connected**
- run `/hooks` — you should see the 4 hooks from project settings
- accept the workspace-trust prompt (project hooks only run in trusted folders)

Get the key at https://developer.ticketmaster.com/ → *My Apps* → copy the **Consumer Key**.
`.env` is git-ignored; never commit it.

## Run

```
/plan-event Team meetup for 40 people in Warsaw on Friday 20 November 2026, 17:00–23:00. Budget 15,000 PLN. Dinner with vegan and gluten-free options, a projector, step-free access.
```
More examples: [`samples/`](samples).

What happens:
1. Claude asks for anything missing (country, dates, guests, budget…) and asks you to **confirm**.
2. It tells you which parts it will plan, then runs the agents (parallel where independent).
3. Each research agent checks options one by one; any option that takes longer than
   2 minutes is declined automatically and the next one is checked.
4. Quality gates run; failures are retried for the affected part only (max 3 times).
5. You get the shortlist to review. **You** record the decision:
   ```
   ! python3 scripts/approve.py <run-id> approve
   ! python3 scripts/approve.py <run-id> reject "Dinner earlier, cheaper hotel"
   ```
   (`!` runs a shell command from the Claude Code prompt; you can also use a normal terminal.)
   Then type `continue`. A rejection triggers a revision and a new approval request.
   Approving only publishes the guide — it books nothing.
6. Output in `runs/<run-id>/output/`: `event-plan.html` and `calendar/` (`program.ics` plus
   one tentative `<part>-<rank>.ics` per option). Pick, contact, book, then keep the
   calendar entry of the option you booked.

### Preview the guide design

```bash
E=.claude/skills/event-html-theme/example/plan.example.json
python3 .claude/skills/ics-calendar/scripts/build_ics.py $E /tmp/cal demo 2026-10-15T09:00:00+00:00
python3 .claude/skills/event-html-theme/scripts/render_html.py $E /tmp/cal /tmp/preview.html 2026-10-15T09:00:00+00:00
```

### Time box
Default 120 s per option, set in `.claude/settings.json` → `env.EVENT_PLANNER_TIMEBOX_SECONDS`.
See what was declined: `python3 scripts/timebox.py status <run-id>`.

## Resume after an interruption

```
/plan-event --resume <run-id>
```
`<run-id>` is the folder name under `runs/` (the last one is also in `runs/.active`).
Completed steps are kept; steps that were running are reset and rerun; a step whose
artifact was modified or deleted is rerun together with everything after it.

Inspect state at any time:
```bash
python3 scripts/state.py show <run-id>
python3 scripts/state.py next <run-id>
```

## Secrets

| Variable | Required | Used by |
|----------|----------|---------|
| `TICKETMASTER_API_KEY` | yes | Ticketmaster MCP server (`.mcp.json` reads it from the environment) |

No secret is stored in the repository. `.env` and `.claude/settings.local.json` are git-ignored,
and Claude is denied read access to `.env`.

## Troubleshooting
- **Ticketmaster calls are denied** — requirements are not confirmed yet, or the call used a
  different `countryCode` than the confirmed country (this is the intended guard).
- **"Output generation is blocked"** — the schedule has no valid approval, or it changed after
  you approved it. Review again and re-run `approve.py`.
- **MCP server not connected** — check `node -v`, that the key is exported in the shell that
  started `claude`, then `/mcp` → reconnect.
