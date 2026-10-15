#!/usr/bin/env python3
"""PostToolUse (Write|Edit|MultiEdit): persist progress and run deterministic checks.

When an artifact or output file of a run is written:
  * its SHA-256 and write time are recorded in workflow-state.json
    (step status stays as is — the coordinator marks 'done' after gates pass);
  * Markdown artifacts are checked with the artifact-validator skill;
  * plan.json is checked with the plan-data skill;
  * .ics / .html outputs (normally written by scripts, but covered if edited by hand)
    are checked with the ics-calendar and event-html-theme skills.
Check failures are returned to Claude (exit 2) so the owning agent fixes them at once.
"""
import subprocess
import sys

from _common import ROOT, feedback, read_input, split_run_path, state

data = read_input()
ti = data.get("tool_input", {}) or {}
path = ti.get("file_path", "")
run, rest = split_run_path(path)
if not run or not (state.state_path(run)).exists():
    raise SystemExit(0)

st = state.load(run)
step = next((s for s, v in st["steps"].items() if v["artifact"] == rest), None)
target = state.run_dir(run) / rest
if step:
    v = st["steps"][step]
    v["last_written_at"] = state.now()
    v["last_written_by"] = data.get("agent_type") or "coordinator"
    if v["status"] == "pending":
        v["status"] = "running"
    state.log(st, f"{rest} written by {v['last_written_by']}")
    state.save(run, st)

SKILLS = ROOT / ".claude" / "skills"
check = None
plan = state.run_dir(run) / "artifacts/plan.json"
if rest.startswith("artifacts/") and rest.endswith(".md"):
    check = [sys.executable, str(SKILLS / "artifact-validator/scripts/check_artifact.py"), str(target)]
elif rest == "artifacts/plan.json":
    check = [sys.executable, str(SKILLS / "plan-data/scripts/plan_tool.py"), "check", str(target)]
elif rest.endswith(".ics"):
    check = [sys.executable, str(SKILLS / "ics-calendar/scripts/validate_ics.py"), str(target)]
elif rest.endswith(".html"):
    check = [sys.executable, str(SKILLS / "event-html-theme/scripts/check_html.py"), str(target),
             "--plan", str(plan)]

if check:
    r = subprocess.run(check, capture_output=True, text=True)
    if r.returncode != 0:
        feedback(f"Deterministic check failed for {rest}:\n{r.stdout}{r.stderr}\n"
                 "Fix the file and write it again.")
