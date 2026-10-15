#!/usr/bin/env python3
"""Populate the predefined HTML template from plan.json (stdlib only). See ../SKILL.md.

  render_html.py <plan.json> <calendar-dir> <out.html> <generated-at ISO>

The page structure lives in template.html and partials/*.html. This script only fills
{{placeholders}}: values are HTML-escaped unless the key ends in `_html` (pre-rendered
partials). Every option's .ics and the program .ics are embedded as data: URIs, so the
guide is a single self-contained file.
"""
import html
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE.parent / "plan-data" / "scripts"))
import plan_tool  # noqa: E402

RANK_LABEL = {1: "Top pick", 2: "Option 2", 3: "Option 3"}
CAT_NOTE = {"accommodation": "Overnight", "transport": "Getting there"}


def partial(name):
    return (HERE / "partials" / f"{name}.html").read_text(encoding="utf-8")


def fill(tpl, values):
    def sub(m):
        key = m.group(1)
        if key not in values:
            raise KeyError(f"no value for placeholder {{{{{key}}}}}")
        v = values[key]
        return str(v) if key.endswith("_html") else html.escape(str(v), quote=True)
    return re.sub(r"\{\{(\w+)\}\}", sub, tpl)


def money(v, cur):
    s = f"{v:,.2f}".replace(",", " ")
    if s.endswith(".00"):
        s = s[:-3]
    return f"{s} {cur}"


def day_label(iso):
    return date.fromisoformat(iso).strftime("%a %-d %b %Y")


def when_label(ev):
    a, b = date.fromisoformat(ev["date_start"]), date.fromisoformat(ev["date_end"])
    if a == b:
        return a.strftime("%a %-d %b %Y")
    if a.month == b.month:
        return f"{a.day}–{b.day} {b.strftime('%b %Y')}"
    return f"{a.strftime('%-d %b')} – {b.strftime('%-d %b %Y')}"


def data_uri(path: Path):
    return "data:text/calendar;charset=utf-8," + quote(path.read_bytes().decode("utf-8"), safe="")


def contacts_html(ct):
    items = [f'<li><a href="{html.escape(ct["website"])}" target="_blank" rel="noopener">Website</a></li>']
    if ct.get("booking"):
        items.append(f'<li><a href="{html.escape(ct["booking"])}" target="_blank" rel="noopener">Book or enquire</a></li>')
    if ct.get("phone"):
        tel = re.sub(r"[^\d+]", "", ct["phone"])
        items.append(f'<li><a href="tel:{tel}">{html.escape(ct["phone"])}</a></li>')
    if ct.get("email"):
        items.append(f'<li><a href="mailto:{html.escape(ct["email"])}">{html.escape(ct["email"])}</a></li>')
    return "\n".join("            " + i for i in items)


def render(plan, cal_dir: Path, generated_at):
    ev = plan["event"]
    cur = ev["currency"]
    b = plan_tool.budget(plan)
    multi_day = ev["date_start"] != ev["date_end"]

    run_items, slots = [], []
    for s in plan["slots"]:
        time = f"{s['start']}–{s['end']}"
        run_items.append(fill(partial("run-item"), {
            "id": s["id"], "title": s["title"],
            "time": (date.fromisoformat(s["date"]).strftime("%a ") if multi_day else "") + s["start"]}))
        tickets = []
        for c in s["candidates"]:
            ics = cal_dir / f"{s['id']}-{c['rank']}.ics"
            why = c.get("why") or []
            tickets.append(fill(partial("ticket"), {
                "top_class": "top" if c["rank"] == 1 else "",
                "slot_id": s["id"], "rank": c["rank"],
                "rank_label": RANK_LABEL.get(c["rank"], f"Option {c['rank']}"),
                "name": c["name"], "website": c["contact"]["website"],
                "summary": c["summary"], "address": c.get("address", ""),
                "facts_html": "\n".join(f"            <li>{html.escape(f)}</li>" for f in c.get("facts") or []),
                "why_html": ("          <p class=\"why\">Why it fits</p>\n          <ul>\n"
                             + "\n".join(f"            <li>{html.escape(w)}</li>" for w in why)
                             + "\n          </ul>") if why else "",
                "contacts_html": contacts_html(c["contact"]),
                "price": money(c["price"]["amount"], cur),
                "price_basis": c["price"].get("basis", ""),
                "ics_name": f"{s['id']}-{c['rank']}.ics", "ics_uri": data_uri(ics)}))
        note = s.get("shortlist_note")
        slots.append(fill(partial("slot"), {
            "id": s["id"], "time": time, "title": s["title"],
            "day": day_label(s["date"]) + (f" to {day_label(s['end_date'])}" if s.get("end_date") else ""),
            "note": s.get("note") or CAT_NOTE.get(s["category"], ""),
            "shortlist_note_html": f'    <p class="shortlist-note">{html.escape(note)}</p>' if note else "",
            "tickets_html": "\n".join(tickets)}))

    rows = [fill(partial("budget-row"), {
        "row_class": "", "label": l["label"], "cheapest": money(l["cheapest"], cur),
        "top_pick": money(l["top_pick"], cur), "priciest": money(l["priciest"], cur)}) for l in b["lines"]]
    rows.append(fill(partial("budget-row"), {
        "row_class": "total", "label": f"Total with {b['contingency_pct']} % contingency",
        "cheapest": money(b["total"]["cheapest"], cur), "top_pick": money(b["total"]["top_pick"], cur),
        "priciest": money(b["total"]["priciest"], cur)}))
    top, limit = b["total"]["top_pick"], b["limit"]
    if b["top_pick_within_budget"]:
        verdict, vcls = f"Top picks fit the budget with {money(limit - top, cur)} to spare.", "ok"
    elif b["cheapest_within_budget"]:
        verdict, vcls = (f"Top picks are {money(top - limit, cur)} over the limit — the cheaper "
                         f"options fit."), "over"
    else:
        verdict, vcls = f"Even the cheapest options are {money(b['total']['cheapest'] - limit, cur)} over the limit.", "over"

    w = plan.get("weather")
    notes = plan.get("notes") or []
    issues = plan.get("open_issues") or []
    notes_cols = []
    if notes:
        notes_cols.append("    <div><h3>Good to know</h3><ul>"
                          + "".join(f"<li>{html.escape(n)}</li>" for n in notes) + "</ul></div>")
    if issues:
        notes_cols.append("    <div><h3>Check when you call</h3><ul>"
                          + "".join(f"<li>{html.escape(n)}</li>" for n in issues) + "</ul></div>")

    seen, sources = set(), []
    for src in sorted(plan.get("sources") or [], key=lambda x: x["title"].lower()):
        if src["url"] not in seen:
            seen.add(src["url"])
            sources.append(fill(partial("source-item"), src))

    page = (HERE / "template.html").read_text(encoding="utf-8")
    page = toggle(page, "weather", bool(w))
    page = toggle(page, "notes", bool(notes_cols))
    values = {
        "lang": ev.get("language", "en"), "title": ev["title"],
        "occasion": ev.get("occasion", ""), "when": when_label(ev),
        "where": f"{ev['city']}, {ev['country']}", "guests": ev["guests"],
        "budget_limit": money(limit, cur), "summary": ev["summary"],
        "run_of_show_html": "\n".join(run_items), "slots_html": "\n".join(slots),
        "budget_rows_html": "\n".join(rows), "budget_verdict": verdict,
        "budget_verdict_class": vcls, "contingency_pct": b["contingency_pct"],
        "meter_fill_pct": f"{min(top / limit * 100, 100):.1f}" if limit else "100",
        "meter_fill_class": "" if top <= limit else "over",
        "meter_label": f"Top picks {money(top, cur)} of {money(limit, cur)} budget",
        "top_pick_total": money(top, cur),
        "program_ics_name": "program.ics", "program_ics_uri": data_uri(cal_dir / "program.ics"),
        "sources_html": "\n".join(sources),
        "generated_date": datetime.fromisoformat(generated_at).strftime("%-d %b %Y"),
    }
    if w:
        values["weather_days_html"] = "\n".join(fill(partial("weather-day"), {
            "day": day_label(d["date"]), "max": round(d["max_c"]), "min": round(d["min_c"]),
            "rain": d["rain"], "wind": round(d["wind_kmh"])}) for d in w["days"])
        values["weather_advice"] = w.get("advice", "")
    if notes_cols:
        values["notes_html"] = "\n".join(notes_cols)
    return fill(page, values)


def toggle(page, name, keep):
    pat = re.compile(rf"<!--IF:{name}-->\n?(.*?)<!--ENDIF:{name}-->\n?", re.S)
    return pat.sub((lambda m: m.group(1)) if keep else "", page)


def main():
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    plan = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    errs = plan_tool.check(plan)
    if errs:
        sys.exit("plan.json is invalid:\n" + "\n".join(errs))
    out = Path(sys.argv[3])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(plan, Path(sys.argv[2]), sys.argv[4]), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
