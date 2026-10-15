#!/usr/bin/env python3
"""Persisted workflow state for /plan-event runs.

The single source of truth for "what has been done, what runs next" is
runs/<run-id>/workflow-state.json. All mutations go through this script so the
state transitions are deterministic and the coordinator never has to guess.

Usage:
  state.py init <run-id> --input "<request text>"
  state.py plan <run-id> --enable venue,live-events,weather,catering,logistics
  state.py set <run-id> <step> <pending|running|done|skipped> [--note TEXT]
  state.py set-meta <run-id> <key> <value>       # e.g. country_code PL, currency PLN
  state.py next <run-id>                          # steps that may run now (parallel group)
  state.py fail <run-id> <step> "<reason>"        # targeted retry + downstream invalidation
  state.py invalidate <run-id> <step> [--reason TEXT]
  state.py resume <run-id>                        # reset interrupted 'running' steps
  state.py show <run-id>
  state.py active                                 # print active run id
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path(__file__).resolve().parent.parent))
RUNS = ROOT / "runs"
ACTIVE = RUNS / ".active"
MAX_RETRIES = 3

# step -> (owner agent, artifact (relative to run dir), dependencies, optional)
STEPS = {
    "requirements": ("requirements-formalizer", "artifacts/requirements.md", [], False),
    "venue":        ("venue-planner",          "artifacts/venue.md",        ["requirements"], False),
    "live-events":  ("live-events-scout",      "artifacts/live-events.md",  ["requirements"], True),
    "weather":      ("weather-planner",        "artifacts/weather.md",      ["requirements"], True),
    "catering":     ("catering-planner",       "artifacts/catering.md",     ["venue"], True),
    "logistics":    ("logistics-planner",      "artifacts/logistics.md",    ["venue"], True),
    "budget":       ("budget-aggregator",      "artifacts/budget.md",
                     ["venue", "live-events", "catering", "logistics"], False),
    "validation":   ("validator",              "artifacts/validation.md",
                     ["venue", "live-events", "weather", "catering", "logistics", "budget"], False),
    "schedule":     ("schedule-builder",       "artifacts/schedule.md",     ["validation"], False),
    "approval":     ("human",                  "approval.json",             ["schedule"], False),
    "ics":          ("ics-builder",            "output/calendar/program.ics", ["approval"], False),
    "html":         ("html-builder",           "output/event-plan.html",    ["ics"], False),
}
SATISFIED = {"done", "skipped"}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_dir(run_id):
    return RUNS / run_id


def state_path(run_id):
    return run_dir(run_id) / "workflow-state.json"


def load(run_id):
    p = state_path(run_id)
    if not p.exists():
        sys.exit(f"error: no state for run '{run_id}' ({p})")
    return json.loads(p.read_text())


def save(run_id, st):
    st["updated_at"] = now()
    p = state_path(run_id)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, indent=2, ensure_ascii=False) + "\n")
    os.replace(tmp, p)  # atomic: a crash never leaves a half-written state file


def log(st, msg):
    st.setdefault("history", []).append({"at": now(), "event": msg})


def dependents(step):
    """All steps that transitively depend on `step`."""
    out, frontier = set(), {step}
    while frontier:
        nxt = {s for s, (_, _, deps, _) in STEPS.items() if frontier & set(deps)} - out
        out |= nxt
        frontier = nxt
    return out


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def approval_valid(run_id):
    """Deterministic approval check shared with the approval_guard hook."""
    d = run_dir(run_id)
    ap = d / "approval.json"
    sched, plan = d / "artifacts" / "schedule.md", d / "artifacts" / "plan.json"
    if not ap.exists():
        return False, "no approval.json (human must run scripts/approve.py)"
    try:
        rec = json.loads(ap.read_text())
    except json.JSONDecodeError:
        return False, "approval.json is not valid JSON"
    if rec.get("decision") != "approved":
        return False, f"decision is '{rec.get('decision')}'"
    if rec.get("schedule_sha256") != sha256(sched) or rec.get("plan_sha256") != sha256(plan):
        return False, "the shortlist changed after it was approved"
    return True, "ok"


# ---------------------------------------------------------------- commands
def cmd_init(a):
    d = run_dir(a.run_id)
    if state_path(a.run_id).exists():
        sys.exit(f"error: run '{a.run_id}' already exists; use resume")
    (d / "artifacts").mkdir(parents=True, exist_ok=True)
    (d / "output").mkdir(parents=True, exist_ok=True)
    (d / "input.md").write_text(a.input.strip() + "\n")
    st = {
        "run_id": a.run_id,
        "created_at": now(),
        "updated_at": now(),
        "meta": {},
        "steps": {
            s: {"owner": o, "artifact": art, "status": "pending", "retries": 0,
                "enabled": not opt, "sha256": None, "notes": []}
            for s, (o, art, _, opt) in STEPS.items()
        },
        "history": [],
    }
    log(st, "run created")
    save(a.run_id, st)
    ACTIVE.write_text(a.run_id + "\n")
    print(f"run {a.run_id} initialised at {d}")


def cmd_plan(a):
    st = load(a.run_id)
    enable = {x.strip() for x in a.enable.split(",") if x.strip()}
    unknown = enable - {s for s, v in STEPS.items() if v[3]}
    if unknown:
        sys.exit(f"error: not optional steps: {sorted(unknown)}")
    for s, (_, _, _, opt) in STEPS.items():
        if not opt:
            continue
        on = s in enable
        st["steps"][s]["enabled"] = on
        if not on and st["steps"][s]["status"] == "pending":
            st["steps"][s]["status"] = "skipped"
        if on and st["steps"][s]["status"] == "skipped":
            st["steps"][s]["status"] = "pending"
    log(st, f"plan: optional steps enabled = {sorted(enable)}")
    save(a.run_id, st)
    print("plan saved; optional enabled:", ", ".join(sorted(enable)) or "(none)")


def cmd_set(a):
    st = load(a.run_id)
    step = st["steps"].get(a.step) or sys.exit(f"error: unknown step {a.step}")
    if a.status == "done":
        art = run_dir(a.run_id) / step["artifact"]
        if not art.exists():
            sys.exit(f"error: cannot mark {a.step} done, {step['artifact']} missing")
        if a.step == "approval":
            ok, why = approval_valid(a.run_id)
            if not ok:
                sys.exit(f"error: approval not valid: {why}")
        step["sha256"] = sha256(art)
    step["status"] = a.status
    if a.note:
        step["notes"].append(a.note)
    log(st, f"{a.step} -> {a.status}" + (f" ({a.note})" if a.note else ""))
    save(a.run_id, st)
    print(f"{a.step}: {a.status}")


def cmd_set_meta(a):
    st = load(a.run_id)
    st["meta"][a.key] = a.value
    log(st, f"meta {a.key}={a.value}")
    save(a.run_id, st)
    print(f"meta {a.key}={a.value}")


def cmd_next(a):
    st = load(a.run_id)
    steps = st["steps"]
    blocked = [s for s, v in steps.items() if v["status"] == "blocked"]
    if blocked:
        print(json.dumps({"status": "blocked", "blocked": blocked}))
        return
    ready = []
    for s, (_, _, deps, _) in STEPS.items():
        v = steps[s]
        if not v["enabled"] or v["status"] != "pending":
            continue
        if all(steps[d]["status"] in SATISFIED for d in deps):
            ready.append({"step": s, "agent": v["owner"], "artifact": v["artifact"],
                          "retry": v["retries"], "feedback": v["notes"][-3:]})
    if not ready and all(v["status"] in SATISFIED for v in steps.values()):
        print(json.dumps({"status": "complete"}))
        return
    print(json.dumps({"status": "ready" if ready else "waiting", "run": ready}, indent=2))


def _invalidate(st, step, reason):
    for d in sorted(dependents(step)):
        v = st["steps"][d]
        if v["status"] in {"done", "running"}:
            v["status"] = "pending"
            v["sha256"] = None
            v["notes"].append(f"regenerate: upstream '{step}' changed ({reason})")
            log(st, f"{d} invalidated because {step} changed")


def cmd_fail(a):
    st = load(a.run_id)
    v = st["steps"][a.step]
    v["retries"] += 1
    v["notes"].append(a.reason)
    if v["retries"] > MAX_RETRIES:
        v["status"] = "blocked"
        log(st, f"{a.step} BLOCKED after {MAX_RETRIES} retries: {a.reason}")
        for d in dependents(a.step):
            if st["steps"][d]["enabled"] and st["steps"][d]["status"] != "skipped":
                st["steps"][d]["status"] = "blocked"
        save(a.run_id, st)
        print(f"{a.step}: BLOCKED (retry limit {MAX_RETRIES} reached)")
        sys.exit(3)
    v["status"] = "pending"
    v["sha256"] = None
    log(st, f"{a.step} failed (retry {v['retries']}/{MAX_RETRIES}): {a.reason}")
    _invalidate(st, a.step, a.reason)
    save(a.run_id, st)
    print(f"{a.step}: pending, retry {v['retries']}/{MAX_RETRIES}; downstream invalidated")


def cmd_invalidate(a):
    st = load(a.run_id)
    v = st["steps"][a.step]
    v["status"] = "pending"
    v["sha256"] = None
    if a.reason:
        v["notes"].append(a.reason)
    _invalidate(st, a.step, a.reason or "manual")
    log(st, f"{a.step} invalidated ({a.reason or 'manual'})")
    save(a.run_id, st)
    print(f"{a.step} and its dependents set to pending")


def cmd_resume(a):
    st = load(a.run_id)
    reset = []
    for s, v in st["steps"].items():
        if v["status"] == "running":
            v["status"] = "pending"
            reset.append(s)
        # a 'done' step whose artifact vanished or changed outside the workflow is redone
        if v["status"] == "done" and s != "approval":
            p = run_dir(a.run_id) / v["artifact"]
            if sha256(p) != v["sha256"]:
                v["status"] = "pending"
                reset.append(s)
                _invalidate(st, s, "artifact missing or modified")
    log(st, f"resumed; reset {reset or 'nothing'}")
    save(a.run_id, st)
    ACTIVE.write_text(a.run_id + "\n")
    print(json.dumps({"resumed": a.run_id, "reset": reset}))


def cmd_show(a):
    st = load(a.run_id)
    print(f"run {st['run_id']}  (updated {st['updated_at']})")
    print("meta:", json.dumps(st["meta"], ensure_ascii=False))
    for s, v in st["steps"].items():
        flag = "" if v["enabled"] else " (disabled)"
        print(f"  {s:<13} {v['status']:<8} retries={v['retries']}{flag}")


def cmd_active(_):
    print(ACTIVE.read_text().strip() if ACTIVE.exists() else "")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("init"); s.add_argument("run_id"); s.add_argument("--input", required=True)
    s = sub.add_parser("plan"); s.add_argument("run_id"); s.add_argument("--enable", default="")
    s = sub.add_parser("set"); s.add_argument("run_id"); s.add_argument("step")
    s.add_argument("status", choices=["pending", "running", "done", "skipped"]); s.add_argument("--note")
    s = sub.add_parser("set-meta"); s.add_argument("run_id"); s.add_argument("key"); s.add_argument("value")
    s = sub.add_parser("next"); s.add_argument("run_id")
    s = sub.add_parser("fail"); s.add_argument("run_id"); s.add_argument("step"); s.add_argument("reason")
    s = sub.add_parser("invalidate"); s.add_argument("run_id"); s.add_argument("step"); s.add_argument("--reason")
    s = sub.add_parser("resume"); s.add_argument("run_id")
    s = sub.add_parser("show"); s.add_argument("run_id")
    sub.add_parser("active")
    a = p.parse_args()
    {"init": cmd_init, "plan": cmd_plan, "set": cmd_set, "set-meta": cmd_set_meta,
     "next": cmd_next, "fail": cmd_fail, "invalidate": cmd_invalidate,
     "resume": cmd_resume, "show": cmd_show, "active": cmd_active}[a.cmd](a)


if __name__ == "__main__":
    main()
