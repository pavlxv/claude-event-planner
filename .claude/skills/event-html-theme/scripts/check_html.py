#!/usr/bin/env python3
"""Deterministic check of the rendered guide. See ../SKILL.md.

  check_html.py <event-plan.html> [--plan plan.json]
"""
import argparse
import json
import re
import sys
from pathlib import Path

ORDER = ["overview", "program", "shortlists", "weather", "budget", "notes", "calendar", "sources"]
MANDATORY = {"overview", "program", "shortlists", "budget", "calendar", "sources"}
LEAKS = [r"workflow-state", r"approval\.json", r"\bartifacts/", r"plan\.json",
         r"\b(requirements|venue|live-events|weather|catering|logistics|budget|validation|schedule)\.md\b",
         r"\bruns/[\w-]+/", r"CLAUDE\.md", r"\.claude/",
         r"\b(requirements-formalizer|venue-planner|live-events-scout|weather-planner|catering-planner|"
         r"logistics-planner|budget-aggregator|schedule-builder|ics-builder|html-builder)\b"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html")
    ap.add_argument("--plan")
    a = ap.parse_args()
    page = Path(a.html).read_text(encoding="utf-8")
    errs = []
    found = re.findall(r'data-section="([\w-]+)"', page)
    for s in sorted(MANDATORY - set(found)):
        errs.append(f"missing mandatory section '{s}'")
    if [s for s in found if s not in ORDER]:
        errs.append(f"unknown sections in {found}")
    known = [s for s in found if s in ORDER]
    if known != sorted(known, key=ORDER.index) or len(set(found)) != len(found):
        errs.append(f"sections out of order or duplicated: {found}")
    if re.search(r"\{\{\w+\}\}|<!--(IF|ENDIF):", page):
        errs.append("unfilled template placeholders remain")
    if re.search(r"<script[^>]+src=|<link[^>]+stylesheet|@import", page, re.I):
        errs.append("external scripts/stylesheets are not allowed (guide must work offline)")
    text_only = re.sub(r'href="data:[^"]*"', "", page)
    leaks = sorted({m.group(0) for p in LEAKS for m in re.finditer(p, text_only)})
    if leaks:
        errs.append(f"internal names visible to the user: {leaks}")
    tickets = re.findall(r'data-option="([\w-]+)"', page)
    cal_links = len(re.findall(r'class="btn" download="[^"]+\.ics" href="data:text/calendar', page))
    if cal_links != len(tickets) + 1:
        errs.append(f"{cal_links} calendar links for {len(tickets)} options + program (expected {len(tickets) + 1})")
    if a.plan:
        plan = json.loads(Path(a.plan).read_text(encoding="utf-8"))
        expected = [f"{s['id']}-{c['rank']}" for s in plan["slots"] for c in s["candidates"]]
        if tickets != expected:
            errs.append(f"options on page {tickets} differ from plan {expected}")
        if bool(plan.get("weather")) != ("weather" in found):
            errs.append("weather section must appear exactly when the plan has weather")
    for e in errs:
        print("FAIL", e)
    if not errs:
        print(f"PASS sections: {', '.join(found)}; {len(tickets)} options, {cal_links} calendar links")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
