#!/usr/bin/env python3
"""PreToolUse (Write|Edit|MultiEdit|Bash): human-approval gate.

1. Claude may never create/alter approval.json or run scripts/approve.py —
   approval must come from the human.
2. Nothing may be written into runs/<id>/output/ unless approval.json says
   'approved' AND its schedule hash equals the current schedule.md.
"""
import re

from _common import deny, read_input, split_run_path, state

data = read_input()
tool = data.get("tool_name", "")
ti = data.get("tool_input", {}) or {}

if tool == "Bash":
    cmd = ti.get("command", "")
    if re.search(r"approve\.py|approval\.json|approval-log\.jsonl", cmd) and not re.search(
        r"^\s*(cat|less|head|jq|python3 -m json\.tool)\b", cmd
    ):
        deny("Approval is recorded only by the human with scripts/approve.py. "
             "Ask the user to run it; do not write or simulate approval.")
    m = re.search(r"runs/([^/\s]+)/output", cmd)
    if m and re.search(r">|build_ics\.py|render_html\.py|\bcp\b|\bmv\b|\btee\b", cmd):
        ok, why = state.approval_valid(m.group(1))
        if not ok:
            deny(f"Output generation is blocked until the schedule is approved: {why}.")
    raise SystemExit(0)

path = ti.get("file_path", "")
run, rest = split_run_path(path)
if not run:
    raise SystemExit(0)

if rest.startswith("approval"):
    deny("approval.json is written only by the human via scripts/approve.py.")

if rest.startswith("output/"):
    ok, why = state.approval_valid(run)
    if not ok:
        deny(f"Output generation is blocked until the schedule is approved: {why}. "
             f"Ask the user to review the schedule and run "
             f"`python3 scripts/approve.py {run} approve` (or reject with feedback).")
