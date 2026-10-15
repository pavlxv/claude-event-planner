#!/usr/bin/env python3
"""PreToolUse (Write|Edit|MultiEdit): keep internal names out of user-facing output.

Applies to files under runs/<id>/output/ (HTML guide, ICS calendar, data JSON shown
to the user). Internal artifact names, state files and run paths must not appear.
"""
import re

from _common import deny, read_input, split_run_path

FORBIDDEN = [
    r"workflow-state", r"approval\.json", r"\bartifacts/",
    r"\b(requirements|venue|live-events|weather|catering|logistics|budget|validation|schedule)\.md\b",
    r"plan\.json", r"\bruns/[\w-]+/", r"CLAUDE\.md", r"\.claude/",
    r"\b(requirements-formalizer|venue-planner|live-events-scout|weather-planner|"
    r"catering-planner|logistics-planner|budget-aggregator|schedule-builder|"
    r"ics-builder|html-builder)\b",
]

data = read_input()
ti = data.get("tool_input", {}) or {}
run, rest = split_run_path(ti.get("file_path", ""))
if not run or not rest.startswith("output/"):
    raise SystemExit(0)

text = ti.get("content") or ti.get("new_string") or ""
for edit in ti.get("edits", []) or []:
    text += "\n" + edit.get("new_string", "")

hits = sorted({m.group(0) for pat in FORBIDDEN for m in re.finditer(pat, text)})
if hits:
    deny("User-facing output must not mention internal workflow names: "
         + ", ".join(hits[:8]) + ". Rephrase in plain words and write again.")
