#!/usr/bin/env python3
"""Deterministic structural + citation check for /plan-event artifacts. See ../SKILL.md."""
import re
import sys
from pathlib import Path

HEADINGS = ["## Summary", "## Details", "## Costs", "## Sources", "## Open issues"]
NO_COSTS = {"requirements", "weather", "validation"}
NO_SOURCES = {"requirements", "validation"}
SUBSECTIONS = {
    "requirements": ["### Confirmed requirements", "### Execution hints", "### Open questions"],
    "venue": ["### Top 3 candidates"],
    "live-events": ["### Top 3 candidates", "### Date conflicts"],
    "weather": ["### Outlook", "### Risk assessment"],
    "catering": ["### Top 3 candidates", "### Dietary coverage"],
    "logistics": ["### Transport", "### Top 3 candidates"],
    "budget": ["### Totals"],
    "validation": ["### Gate results"],
    "schedule": ["### Program", "### Options per slot"],
}
SHORTLIST = {"venue", "live-events", "catering", "logistics"}
URL = re.compile(r"https?://[^\s)>\]]+")
NUM = re.compile(r"^-?\d+(?:[.,]\d+)?$")
CONTACT = re.compile(r"https?://\S+|\+?\d[\d ()-]{6,}\d|[\w.+-]+@[\w-]+\.[\w.]+")


def shortlist_errors(text):
    """### Top 3 candidates must hold '#### 1. Name' … '#### 3. Name' blocks with
    Website / Book / Price / Source lines. Fewer than 3 only with a 'Shortlist note:' line."""
    m = re.search(r"^### Top 3 candidates\s*$(.*?)(?=^### |^## |\Z)", text, re.M | re.S)
    if not m:
        return []
    body = m.group(1)
    blocks = re.split(r"^#### ", body, flags=re.M)[1:]
    errs = []
    nums = [int(x.group(1)) for x in (re.match(r"(\d+)\.\s+\S", b) for b in blocks) if x]
    if len(blocks) != 3 and not re.search(r"^Shortlist note:\s*\S", body, re.M):
        errs.append(f"shortlist: {len(blocks)} candidates, need exactly 3 "
                    "(or a 'Shortlist note:' line explaining why fewer)")
    if nums != list(range(1, len(blocks) + 1)):
        errs.append(f"shortlist: candidates must be headed '#### 1. Name', '#### 2. …' (got {nums})")
    for b in blocks:
        name = b.splitlines()[0].strip()
        fields = {k: (re.search(rf"^- {k}:\s*(.+)$", b, re.M) or [None, ""])[1].strip()
                  for k in ("Website", "Book", "Price", "Source")}
        if not URL.search(fields["Website"]):
            errs.append(f"shortlist: '{name}' needs '- Website: <url>'")
        if not CONTACT.search(fields["Book"]):
            errs.append(f"shortlist: '{name}' needs '- Book: <booking url | phone | email>'")
        if not re.search(r"\d", fields["Price"]):
            errs.append(f"shortlist: '{name}' needs '- Price: <amount> <CUR> (<basis>)'")
        if not URL.search(fields["Source"]):
            errs.append(f"shortlist: '{name}' needs '- Source: <url>'")
    return errs


def num(s):
    s = s.strip().replace(" ", "").replace(" ", "")
    if not NUM.match(s):
        return None
    return float(s.replace(",", "."))


def section(text, heading):
    m = re.search(rf"^{re.escape(heading)}\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1) if m else ""


def check(path: Path):
    errs = []
    text = path.read_text(encoding="utf-8")
    kind = path.stem
    if not re.match(r"^# \S", text):
        errs.append("title: first line must be '# <Title>'")
    meta = {k: (re.search(rf"^- {k}:\s*(.+)$", text, re.M) or [None, None])[1]
            for k in ("Artifact", "Owner", "Run", "Revision")}
    for k, v in meta.items():
        if not v:
            errs.append(f"metadata: missing '- {k}:' bullet")
    if meta["Artifact"] and meta["Artifact"].strip() != kind:
        errs.append(f"metadata: Artifact '{meta['Artifact'].strip()}' != file name '{kind}'")
    if meta["Revision"] and not meta["Revision"].strip().isdigit():
        errs.append("metadata: Revision must be an integer")

    required = [h for h in HEADINGS if not (h == "## Costs" and kind in NO_COSTS)]
    positions = []
    for h in required:
        m = re.search(rf"^{re.escape(h)}\s*$", text, re.M)
        if not m:
            errs.append(f"structure: missing heading '{h}'")
        else:
            positions.append(m.start())
    if positions != sorted(positions):
        errs.append("structure: headings out of order " + " → ".join(required))

    details = section(text, "## Details")
    for sub in SUBSECTIONS.get(kind, []):
        if not re.search(rf"^{re.escape(sub)}\s*$", details, re.M):
            errs.append(f"details: missing '{sub}'")

    if kind in SHORTLIST:
        errs += shortlist_errors(details)

    if kind not in NO_SOURCES and not URL.search(section(text, "## Sources")):
        errs.append("citations: '## Sources' needs at least one http(s) link")

    if kind not in NO_COSTS:
        rows = [r for r in section(text, "## Costs").splitlines() if r.strip().startswith("|")]
        body = [r for r in rows[2:]] if len(rows) >= 2 else []
        for r in body:
            cells = [c.strip() for c in r.strip().strip("|").split("|")]
            if len(cells) < 6:
                errs.append(f"costs: row needs 6 columns: {r.strip()}")
                continue
            item, qty, unit, total, cur, src = cells[:6]
            q, u, t = num(qty), num(unit), num(total)
            if None in (q, u, t):
                errs.append(f"costs: non-numeric Qty/Unit/Total in '{item}'")
            elif abs(q * u - t) > 0.01:
                errs.append(f"costs: {item}: {qty} × {unit} ≠ {total}")
            if not re.fullmatch(r"[A-Z]{3}", cur):
                errs.append(f"costs: '{item}' currency must be ISO 4217 (e.g. EUR)")
            if not (URL.search(src) or (kind in ("budget", "schedule") and src)):
                errs.append(f"citations: cost '{item}' has no source URL")
    return errs


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: check_artifact.py <artifact.md | artifacts-dir>")
    target = Path(sys.argv[1])
    files = sorted(target.glob("*.md")) if target.is_dir() else [target]
    failed = False
    for f in files:
        errs = check(f)
        if errs:
            failed = True
            for e in errs:
                print(f"FAIL {f.name} {e}")
        else:
            print(f"PASS {f.name}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
