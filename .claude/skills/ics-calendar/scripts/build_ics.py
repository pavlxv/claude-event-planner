#!/usr/bin/env python3
"""Build RFC 5545 calendars from plan.json (stdlib only). See ../SKILL.md.

Output directory gets:
  program.ics                  one TENTATIVE event per slot; description lists the options
  <slot-id>-<rank>.ics         one TENTATIVE event per option, with its booking contacts
"""
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

PRODID = "-//event-planner//plan-event workflow//EN"


def esc(text):
    return (str(text).replace("\\", "\\\\").replace(";", "\\;")
            .replace(",", "\\,").replace("\r\n", "\\n").replace("\n", "\\n"))


def fold(line):
    """Fold to ≤75 octets per line without splitting UTF-8 characters."""
    out, cur = [], b""
    for ch in line:
        b = ch.encode("utf-8")
        if len(cur) + len(b) > (75 if not out else 74):
            out.append(cur)
            cur = b""
        cur += b
    out.append(cur)
    return "\r\n ".join(x.decode("utf-8") for x in out)


def utc(day, hhmm, tz):
    dt = datetime.fromisoformat(f"{day}T{hhmm}").replace(tzinfo=ZoneInfo(tz))
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "x"


def contacts(c):
    ct = c["contact"]
    parts = [f"Website: {ct['website']}"]
    if ct.get("booking"):
        parts.append(f"Book: {ct['booking']}")
    if ct.get("phone"):
        parts.append(f"Phone: {ct['phone']}")
    if ct.get("email"):
        parts.append(f"E-mail: {ct['email']}")
    return parts


def vevent(uid, stamp, s, tz, summary, location, desc, url):
    end_day = s.get("end_date") or s["date"]
    lines = ["BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{stamp}",
             f"DTSTART:{utc(s['date'], s['start'], tz)}", f"DTEND:{utc(end_day, s['end'], tz)}",
             f"SUMMARY:{esc(summary)}", "STATUS:TENTATIVE", "TRANSP:TRANSPARENT"]
    if location:
        lines.append(f"LOCATION:{esc(location)}")
    lines.append(f"DESCRIPTION:{esc(desc)}")
    if url:
        lines.append(f"URL:{url}")
    lines.append("END:VEVENT")
    return lines


def calendar(name, tz, events):
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:{PRODID}", "CALSCALE:GREGORIAN",
             "METHOD:PUBLISH", f"X-WR-CALNAME:{esc(name)}", f"X-WR-TIMEZONE:{tz}"]
    for e in events:
        lines += e
    lines.append("END:VCALENDAR")
    return ("\r\n".join(fold(l) for l in lines) + "\r\n").encode("utf-8")


def uid(*parts):
    return hashlib.sha1(":".join(parts).encode()).hexdigest()[:20] + "@event-planner"


def build(plan, out_dir: Path, run_id, stamp_iso):
    ev = plan["event"]
    tz, cur = ev["timezone"], ev["currency"]
    stamp = datetime.fromisoformat(stamp_iso).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.ics"):
        old.unlink()  # rebuilds never leave options from an earlier revision behind
    program, written = [], []
    for s in plan["slots"]:
        opts = [f"{c['rank']}. {c['name']} — {c['price']['amount']:.2f} {cur} "
                f"({'; '.join(contacts(c))})" for c in s["candidates"]]
        desc = ("Not booked yet. Choose one option and book it directly:\n" + "\n".join(opts))
        program.append(vevent(uid(run_id, s["id"]), stamp, s, tz,
                              f"{s['title']} (to choose)", "", desc, ""))
        for c in s["candidates"]:
            d = "\n".join([f"Option {c['rank']} for: {s['title']}", c["summary"],
                           f"Price: {c['price']['amount']:.2f} {cur}"
                           + (f" ({c['price']['basis']})" if c["price"].get("basis") else ""),
                           "Not booked yet — contact them to reserve."] + contacts(c))
            f = out_dir / f"{s['id']}-{c['rank']}.ics"
            f.write_bytes(calendar(f"{ev['title']} — {c['name']}", tz, [vevent(
                uid(run_id, s["id"], slug(c["name"])), stamp, s, tz,
                f"{s['title']}: {c['name']}", c.get("address", ""), d,
                c["contact"].get("booking") or c["contact"]["website"])]))
            written.append(f.name)
    (out_dir / "program.ics").write_bytes(calendar(ev["title"], tz, program))
    return ["program.ics"] + written


def main():
    if len(sys.argv) != 5:
        sys.exit("usage: build_ics.py <plan.json> <out-dir> <run-id> <generated-at ISO>")
    plan = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    files = build(plan, Path(sys.argv[2]), sys.argv[3], sys.argv[4])
    print(f"wrote {len(files)} calendars to {sys.argv[2]}: {', '.join(files)}")


if __name__ == "__main__":
    main()
