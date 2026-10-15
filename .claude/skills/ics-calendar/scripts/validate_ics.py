#!/usr/bin/env python3
"""Deterministic RFC 5545 checks for the event calendars (stdlib only). See ../SKILL.md.

  validate_ics.py <file.ics | calendar-dir> [--plan plan.json]

With --plan (directory mode): program.ics must have one event per slot and there must be
one <slot>-<rank>.ics per option, each with exactly one event.
"""
import argparse
import json
import re
import sys
from pathlib import Path

REQUIRED = ["UID", "DTSTAMP", "DTSTART", "DTEND", "SUMMARY"]
UTC_TS = re.compile(r"^\d{8}T\d{6}Z$")


def unfold(raw):
    return re.sub(r"\r\n[ \t]", "", raw).split("\r\n")


def check_file(p: Path):
    errs = []
    raw_b = p.read_bytes()
    raw = raw_b.decode("utf-8", errors="replace")
    if re.search(r"(?<!\r)\n", raw):
        errs.append("line endings must be CRLF")
    for i, line in enumerate(raw_b.split(b"\r\n"), 1):
        if len(line) > 75:
            errs.append(f"line {i} is {len(line)} octets (>75, not folded)")
    lines = [l for l in unfold(raw) if l]
    if not lines or lines[0] != "BEGIN:VCALENDAR" or lines[-1] != "END:VCALENDAR":
        errs.append("must start with BEGIN:VCALENDAR and end with END:VCALENDAR")
    if "VERSION:2.0" not in lines:
        errs.append("missing VERSION:2.0")
    if not any(l.startswith("PRODID:") for l in lines):
        errs.append("missing PRODID")
    events, cur = [], None
    for l in lines:
        if l == "BEGIN:VEVENT":
            cur = {}
        elif l == "END:VEVENT":
            events.append(cur)
            cur = None
        elif cur is not None and ":" in l:
            k, v = l.split(":", 1)
            cur[k.split(";")[0]] = v
    uids = set()
    for n, ev in enumerate(events, 1):
        for k in REQUIRED:
            if k not in ev:
                errs.append(f"event {n}: missing {k}")
        for k in ("DTSTAMP", "DTSTART", "DTEND"):
            if k in ev and not UTC_TS.match(ev[k]):
                errs.append(f"event {n}: {k} must be UTC YYYYMMDDTHHMMSSZ, got {ev[k]}")
        if ev.get("DTSTART", "") >= ev.get("DTEND", "~"):
            errs.append(f"event {n}: DTEND must be after DTSTART")
        if ev.get("UID") in uids:
            errs.append(f"event {n}: duplicate UID")
        uids.add(ev.get("UID"))
    if not events:
        errs.append("no events")
    return events, [f"{p.name}: {e}" for e in errs]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--plan")
    a = ap.parse_args()
    t = Path(a.target)
    files = sorted(t.glob("*.ics")) if t.is_dir() else [t]
    errs, counts = [], {}
    for f in files:
        evs, e = check_file(f)
        counts[f.name] = len(evs)
        errs += e
    if a.plan:
        plan = json.loads(Path(a.plan).read_text(encoding="utf-8"))
        slots = plan["slots"]
        if counts.get("program.ics") != len(slots):
            errs.append(f"program.ics has {counts.get('program.ics')} events, plan has {len(slots)} slots")
        expected = {f"{s['id']}-{c['rank']}.ics" for s in slots for c in s["candidates"]}
        have = set(counts) - {"program.ics"}
        for m in sorted(expected - have):
            errs.append(f"missing option calendar {m}")
        for x in sorted(have - expected):
            errs.append(f"unexpected calendar {x}")
        for f in expected & have:
            if counts[f] != 1:
                errs.append(f"{f} must contain exactly one event")
    for e in errs:
        print("FAIL", e)
    if not errs:
        print(f"PASS {len(files)} calendars, {sum(counts.values())} events")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
