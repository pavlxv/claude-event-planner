#!/usr/bin/env python3
"""PreToolUse (mcp__ticketmaster__.*): keep every search inside the confirmed country.

The confirmed ISO-3166 alpha-2 code is stored in workflow-state.json -> meta.country_code
by the coordinator after the user confirms the requirements.
"""
from _common import active_run, deny, read_input, state

data = read_input()
ti = data.get("tool_input", {}) or {}
run = active_run()
if not run:
    deny("No active /plan-event run. Start one with /plan-event before searching Ticketmaster.")

try:
    meta = state.load(run).get("meta", {})
except SystemExit:
    deny(f"Active run '{run}' has no state file.")

expected = (meta.get("country_code") or "").upper()
given = (ti.get("countryCode") or "").upper()

if not expected:
    deny("Requirements are not confirmed yet (no country_code in run state). "
         "Confirm the requirements first.")
if given != expected:
    deny(f"Ticketmaster searches must be scoped to the confirmed country: "
         f"set countryCode='{expected}' (got '{given or 'missing'}').")
# no output = no decision; the normal permission flow applies
