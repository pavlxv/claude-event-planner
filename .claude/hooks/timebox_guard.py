#!/usr/bin/env python3
"""PreToolUse (WebFetch|WebSearch|mcp__.*): 2-minute time box per option.

For research subagents only:
  * WebFetch (checking a specific option's pages) requires an announced option:
    `python3 scripts/timebox.py start <run> <agent> "<option>"`.
  * When the announced option has taken longer than the limit, the option is
    recorded as declined and every further web/MCP call is denied until the agent
    starts the next option. Discovery searches (WebSearch, MCP lists) are allowed
    while no option is in progress.
"""
import sys

from _common import ROOT, active_run, deny, read_input

sys.path.insert(0, str(ROOT / "scripts"))
import timebox  # noqa: E402

RESEARCH_AGENTS = {"venue-planner", "live-events-scout", "catering-planner", "logistics-planner"}

data = read_input()
agent_name = data.get("agent_type") or ""
if agent_name not in RESEARCH_AGENTS:
    raise SystemExit(0)
run = active_run()
if not run:
    raise SystemExit(0)

tb = timebox.load(run)
a = timebox.agent(tb, agent_name)
limit = tb["limit_seconds"]
cur = a["current"]

if cur and timebox.elapsed(a) > limit:
    declined = timebox.close_current(a, "declined", f"time box of {limit}s exceeded")
    timebox.save(run, tb)
    deny(f"Time box exceeded: '{declined['option']}' took more than {limit}s and is now "
         f"DECLINED. Do not research it further. Record it under '### Declined options' "
         f"in your artifact, then start the next option from your long list with "
         f"`python3 scripts/timebox.py start {run} {agent_name} \"<next option>\"`.")

if not cur and data.get("tool_name") == "WebFetch":
    deny(f"Announce the option you are checking before fetching its pages: "
         f"`python3 scripts/timebox.py start {run} {agent_name} \"<option name>\"` "
         f"(each option gets {limit}s).")
