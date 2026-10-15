#!/usr/bin/env python3
"""Record the HUMAN approval decision for a run.

Run this yourself (in your terminal, or with the `!` prefix inside Claude Code):

  python3 scripts/approve.py <run-id> approve
  python3 scripts/approve.py <run-id> reject "Move dinner to 19:00 and drop the boat trip"

The decision is bound to the exact shortlist you reviewed: approval.json stores the
SHA-256 of artifacts/schedule.md and artifacts/plan.json. If the schedule changes afterwards, the approval is
no longer valid and the output builders are blocked by the approval_guard hook.
Claude is blocked from writing approval.json or running this script.
"""
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path(__file__).resolve().parent.parent))


def main():
    if len(sys.argv) < 3 or sys.argv[2] not in {"approve", "reject"}:
        sys.exit(__doc__)
    run_id, decision = sys.argv[1], sys.argv[2]
    feedback = " ".join(sys.argv[3:]).strip()
    run = ROOT / "runs" / run_id
    schedule = run / "artifacts" / "schedule.md"
    plan = run / "artifacts" / "plan.json"
    if not schedule.exists() or not plan.exists():
        sys.exit(f"error: {schedule} does not exist yet — nothing to approve")
    if decision == "reject" and not feedback:
        sys.exit("error: a rejection needs feedback text so the plan can be revised")
    record = {
        "run_id": run_id,
        "decision": "approved" if decision == "approve" else "rejected",
        "feedback": feedback,
        "schedule_sha256": hashlib.sha256(schedule.read_bytes()).hexdigest(),
        "plan_sha256": hashlib.sha256(plan.read_bytes()).hexdigest(),
        "decided_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "decided_by": os.environ.get("USER", "human"),
    }
    (run / "approval.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    # keep an audit trail of every decision
    with (run / "approval-log.jsonl").open("a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"{record['decision']}: run {run_id} (schedule {record['schedule_sha256'][:12]}…)")
    print("Now tell Claude: 'continue' (or run /plan-event --resume", run_id + ")")


if __name__ == "__main__":
    main()
