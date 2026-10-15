#!/usr/bin/env python3
"""plan.json validator, budget calculator and schedule.md renderer. See ../SKILL.md."""
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

CATEGORIES = {"venue", "live-event", "catering", "accommodation", "transport", "activity"}
TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
HTTPS = re.compile(r"^https?://\S+$")
CONTINGENCY = 0.10


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def d(s):
    return date.fromisoformat(s)


# ------------------------------------------------------------------ check
def check(plan):
    errs = []
    ev = plan.get("event") or {}
    for k in ("title", "summary", "city", "country", "country_code", "timezone",
              "date_start", "date_end", "guests", "budget_limit", "currency"):
        if ev.get(k) in (None, ""):
            errs.append(f"event.{k} is missing")
    if errs:
        return errs
    cur = ev["currency"]
    start, end = d(ev["date_start"]), d(ev["date_end"])
    slots = plan.get("slots") or []
    if not slots:
        errs.append("plan has no slots")
    keys = []
    ids = set()
    for s in slots:
        sid = s.get("id", "?")
        p = f"slot '{sid}'"
        if sid in ids:
            errs.append(f"{p}: duplicate id")
        ids.add(sid)
        if s.get("category") not in CATEGORIES:
            errs.append(f"{p}: category must be one of {sorted(CATEGORIES)}")
        for k in ("start", "end"):
            if not TIME.match(str(s.get(k, ""))):
                errs.append(f"{p}: {k} must be HH:MM")
        try:
            sd = d(s["date"])
            ed = d(s["end_date"]) if s.get("end_date") else sd
            if not (start <= sd <= end):
                errs.append(f"{p}: date {sd} outside {start}..{end}")
            if ed > end + timedelta(days=1) or ed < sd:
                errs.append(f"{p}: end_date {ed} not valid")
            if ed == sd and s.get("end", "") <= s.get("start", ""):
                errs.append(f"{p}: end must be after start (set end_date for overnight)")
            keys.append((s["date"], s.get("start", "")))
        except (KeyError, ValueError):
            errs.append(f"{p}: date must be YYYY-MM-DD")
        cands = s.get("candidates") or []
        if len(cands) != 3 and not s.get("shortlist_note"):
            errs.append(f"{p}: needs exactly 3 candidates (has {len(cands)}); "
                        "add 'shortlist_note' if fewer exist")
        if len(cands) > 3:
            errs.append(f"{p}: more than 3 candidates")
        ranks = [c.get("rank") for c in cands]
        if ranks != list(range(1, len(cands) + 1)):
            errs.append(f"{p}: ranks must be 1..{len(cands)} in order, got {ranks}")
        names = [c.get("name", "").strip().lower() for c in cands]
        if len(set(names)) != len(names):
            errs.append(f"{p}: duplicate candidate names")
        for c in cands:
            q = f"{p} option '{c.get('name', '?')}'"
            for k in ("name", "summary"):
                if not c.get(k):
                    errs.append(f"{q}: missing {k}")
            pr = c.get("price") or {}
            if not isinstance(pr.get("amount"), (int, float)) or pr["amount"] < 0:
                errs.append(f"{q}: price.amount must be a number ≥ 0")
            if pr.get("currency") != cur:
                errs.append(f"{q}: price.currency must be {cur}")
            ct = c.get("contact") or {}
            if not HTTPS.match(str(ct.get("website") or "")):
                errs.append(f"{q}: contact.website must be a URL")
            if not any(ct.get(k) for k in ("booking", "phone", "email")):
                errs.append(f"{q}: needs at least one of contact.booking / phone / email")
            if not HTTPS.match(str(c.get("source") or "")):
                errs.append(f"{q}: source must be a URL")
    if keys != sorted(keys):
        errs.append("slots must be sorted by date and start time")
    for src in plan.get("sources") or []:
        if not HTTPS.match(str(src.get("url", ""))):
            errs.append(f"source '{src.get('title')}' has no URL")
    return errs


# ------------------------------------------------------------------ budget
def budget(plan):
    ev = plan["event"]
    lines = []
    for s in plan["slots"]:
        amounts = [c["price"]["amount"] for c in s["candidates"]]
        top = next(c for c in s["candidates"] if c["rank"] == 1)["price"]["amount"]
        lines.append({"slot": s["id"], "label": s["title"], "cheapest": min(amounts),
                      "top_pick": top, "priciest": max(amounts)})
    tot = {k: sum(l[k] for l in lines) for k in ("cheapest", "top_pick", "priciest")}
    with_c = {k: round(v * (1 + CONTINGENCY), 2) for k, v in tot.items()}
    limit = ev["budget_limit"]
    return {"currency": ev["currency"], "limit": limit, "contingency_pct": int(CONTINGENCY * 100),
            "lines": lines, "subtotal": tot, "total": with_c,
            "top_pick_within_budget": with_c["top_pick"] <= limit,
            "cheapest_within_budget": with_c["cheapest"] <= limit}


# ------------------------------------------------------------------ markdown
def money(v, cur):
    return f"{v:,.2f} {cur}".replace(",", " ")


def to_md(plan, run_id):
    ev, b = plan["event"], budget(plan)
    cur = ev["currency"]
    out = [f"# Event shortlist — {ev['title']}", "", "- Artifact: schedule",
           "- Owner: schedule-builder", f"- Run: {run_id}", "- Revision: 1", "",
           "## Summary", ev["summary"], "",
           f"Nothing is booked. Each part of the event has up to three options with booking "
           f"contacts. Top picks total {money(b['total']['top_pick'], cur)} "
           f"(with {b['contingency_pct']} % contingency) against a limit of {money(b['limit'], cur)}.",
           "", "## Details", "", "### Program",
           "| Date | Start | End | Item | Location | Address | Link |",
           "|------|-------|-----|------|----------|---------|------|"]
    for s in plan["slots"]:
        top = s["candidates"][0]
        out.append(f"| {s['date']} | {s['start']} | {s['end']} | {s['title']} | "
                   f"Top pick: {top['name']} | {top.get('address', '')} | {top['contact']['website']} |")
    out += ["", "### Options per slot"]
    for s in plan["slots"]:
        out += ["", f"#### {s['title']} ({s['date']} {s['start']}–{s['end']})"]
        if s.get("shortlist_note"):
            out.append(f"_{s['shortlist_note']}_")
        for c in s["candidates"]:
            ct = c["contact"]
            book = " · ".join(x for x in (ct.get("booking"), ct.get("phone"), ct.get("email")) if x)
            out.append(f"{c['rank']}. **{c['name']}** — {money(c['price']['amount'], cur)} "
                       f"({c['price'].get('basis', '')}). {c['summary']} Book: {book}. "
                       f"Website: {ct['website']}")
    out += ["", "### Budget overview",
            "| Slot | Cheapest | Top pick | Priciest |", "|------|---:|---:|---:|"]
    for l in b["lines"]:
        out.append(f"| {l['label']} | {money(l['cheapest'], cur)} | {money(l['top_pick'], cur)} | "
                   f"{money(l['priciest'], cur)} |")
    out.append(f"| **Total incl. {b['contingency_pct']} % contingency** | "
               f"{money(b['total']['cheapest'], cur)} | {money(b['total']['top_pick'], cur)} | "
               f"{money(b['total']['priciest'], cur)} |")
    out += ["", "## Costs", "| Item | Qty | Unit price | Total | Currency | Source |",
            "|------|-----|-----------:|------:|----------|--------|"]
    for s in plan["slots"]:
        top = s["candidates"][0]
        a = top["price"]["amount"]
        out.append(f"| {s['title']}: {top['name']} | 1 | {a:.2f} | {a:.2f} | {cur} | {top['source']} |")
    out += ["", "## Sources"]
    out += [f"- [{x['title']}]({x['url']})" for x in plan.get("sources") or []]
    out += ["", "## Open issues"]
    out += [f"- {x}" for x in plan.get("open_issues") or []] or ["- None"]
    return "\n".join(out) + "\n"


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in {"check", "to-md", "budget"}:
        sys.exit("usage: plan_tool.py check|budget <plan.json> | to-md <plan.json> <run-id>")
    plan = load(sys.argv[2])
    if sys.argv[1] == "check":
        errs = check(plan)
        for e in errs:
            print("FAIL", e)
        if not errs:
            n = sum(len(s["candidates"]) for s in plan["slots"])
            print(f"PASS {len(plan['slots'])} slots, {n} options")
        sys.exit(1 if errs else 0)
    errs = check(plan)
    if errs:
        sys.exit("plan.json is invalid, run 'check' first:\n" + "\n".join(errs))
    if sys.argv[1] == "budget":
        print(json.dumps(budget(plan), indent=2))
    else:
        if len(sys.argv) < 4:
            sys.exit("to-md needs <run-id>")
        sys.stdout.write(to_md(plan, sys.argv[3]))


if __name__ == "__main__":
    main()
