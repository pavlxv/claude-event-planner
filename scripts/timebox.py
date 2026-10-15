#!/usr/bin/env python3
"""Per-option time box for research agents (default 120 s per option).

Research agents announce which option they are checking; the timebox_guard hook
denies further web/MCP calls once that option has taken longer than the limit,
records it as declined, and tells the agent to move to the next option.

Usage (from inside an agent, via Bash):
  python3 scripts/timebox.py start  <run-id> <agent-name> "<option name>"
  python3 scripts/timebox.py done   <run-id> <agent-name>            # option checked OK
  python3 scripts/timebox.py drop   <run-id> <agent-name> "<reason>" # reject it yourself
  python3 scripts/timebox.py status <run-id> [<agent-name>]

Limit: env EVENT_PLANNER_TIMEBOX_SECONDS (default 120).
"""
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path(__file__).resolve().parent.parent))
LIMIT = int(os.environ.get("EVENT_PLANNER_TIMEBOX_SECONDS", "120"))


def path(run_id):
    return ROOT / "runs" / run_id / "timebox.json"


def load(run_id):
    p = path(run_id)
    if p.exists():
        return json.loads(p.read_text())
    return {"limit_seconds": LIMIT, "agents": {}}


def save(run_id, data):
    p = path(run_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    os.replace(tmp, p)


def stamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def agent(data, name):
    return data["agents"].setdefault(name, {"current": None, "done": [], "declined": []})


def close_current(a, outcome, reason=""):
    cur = a.get("current")
    if not cur:
        return None
    cur = dict(cur, ended_at=stamp(), seconds=round(time.time() - cur["started_ts"]))
    if outcome == "done":
        a["done"].append(cur)
    else:
        a["declined"].append(dict(cur, reason=reason))
    a["current"] = None
    return cur


def elapsed(a):
    cur = a.get("current")
    return time.time() - cur["started_ts"] if cur else 0.0


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd, run_id = sys.argv[1], sys.argv[2]
    data = load(run_id)
    if cmd == "status":
        names = sys.argv[3:4] or list(data["agents"])
        for n in names:
            a = agent(data, n)
            cur = a["current"]
            print(f"{n}: current={cur['option'] if cur else '-'} "
                  f"({int(elapsed(a))}s/{data['limit_seconds']}s) "
                  f"done={len(a['done'])} declined={len(a['declined'])}")
        return
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    a = agent(data, sys.argv[3])
    if cmd == "start":
        if len(sys.argv) < 5:
            sys.exit("start needs an option name")
        if a["current"] and elapsed(a) > data["limit_seconds"]:
            close_current(a, "declined", "time box exceeded")
        else:
            close_current(a, "done")  # moving on implies the previous option was finished
        a["current"] = {"option": sys.argv[4], "started_at": stamp(), "started_ts": time.time()}
        save(run_id, data)
        print(f"time box started: '{sys.argv[4]}' — {data['limit_seconds']}s")
    elif cmd == "done":
        cur = close_current(a, "done")
        save(run_id, data)
        print(f"done: {cur['option']} in {cur['seconds']}s" if cur else "nothing in progress")
    elif cmd == "drop":
        reason = " ".join(sys.argv[4:]) or "rejected by agent"
        cur = close_current(a, "declined", reason)
        save(run_id, data)
        print(f"declined: {cur['option']} ({reason})" if cur else "nothing in progress")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
