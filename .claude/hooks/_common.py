"""Shared helpers for the workflow hooks (stdlib only)."""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
sys.path.insert(0, str(ROOT / "scripts"))
import state  # noqa: E402  (scripts/state.py)

RUN_PATH = re.compile(r"runs/(?P<run>[^/]+)/(?P<rest>.+)$")


def read_input():
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError:
        return {}


def deny(reason):
    """PreToolUse: block the call and tell Claude why."""
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason}}))
    sys.exit(0)


def feedback(msg):
    """PostToolUse: the tool already ran; exit 2 shows stderr to Claude."""
    print(msg, file=sys.stderr)
    sys.exit(2)


def split_run_path(file_path):
    """'…/runs/<id>/artifacts/x.md' -> ('<id>', 'artifacts/x.md') or (None, None)."""
    if not file_path:
        return None, None
    try:
        rel = Path(file_path).resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        rel = file_path.replace("\\", "/")
    m = RUN_PATH.search(rel)
    return (m.group("run"), m.group("rest")) if m else (None, None)


def active_run():
    return state.ACTIVE.read_text().strip() if state.ACTIVE.exists() else None
