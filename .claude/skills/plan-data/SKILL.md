---
name: plan-data
description: Schema, validator and Markdown renderer for plan.json — the structured event shortlist (time slots, each with top-3 options and booking contacts) that feeds approval, the calendars and the HTML guide. Use when writing or checking the event plan data.
---

# plan.json — the single structured source of the final plan

`schedule-builder` writes `runs/<run-id>/artifacts/plan.json`. Everything shown to the
user is generated from it by scripts, so the same plan always renders the same way:

```
plan.json ──plan_tool.py to-md──▶ schedule.md      (what the human approves)
          ──build_ics.py────────▶ calendar/*.ics   (program + one file per option)
          ──render_html.py──────▶ event-plan.html  (predefined template, populated)
```

Nothing is booked. Each option carries the contacts the user needs to book it themselves.

## Schema (version 1)

```json
{
  "schema_version": 1,
  "event": {
    "title": "Team meetup", "occasion": "Company team evening",
    "summary": "2–3 plain sentences: what, where, for whom.",
    "city": "Warsaw", "country": "Poland", "country_code": "PL",
    "timezone": "Europe/Warsaw", "date_start": "2026-11-20", "date_end": "2026-11-20",
    "guests": 40, "budget_limit": 15000, "currency": "PLN", "language": "en"
  },
  "slots": [
    {
      "id": "venue", "category": "venue",
      "title": "Venue for the evening",
      "date": "2026-11-20", "start": "17:00", "end": "23:00", "end_date": null,
      "note": "Optional one line shown under the slot title.",
      "candidates": [
        {
          "rank": 1, "name": "Loft Example",
          "summary": "One sentence on what it is.",
          "address": "ul. Długa 1, 00-001 Warszawa",
          "price": {"amount": 4000, "currency": "PLN", "basis": "room hire, 6 hours"},
          "facts": ["Up to 60 seated", "Step-free entrance"],
          "why": ["Projector and screen included", "10 minutes from the centre"],
          "contact": {"website": "https://…", "booking": "https://…/contact",
                      "phone": "+48 22 000 00 00", "email": "events@example.com"},
          "source": "https://…"
        }
      ]
    }
  ],
  "weather": {"method": "forecast | climate",
              "days": [{"date": "2026-11-20", "min_c": 1, "max_c": 6, "rain": "40%", "wind_kmh": 25}],
              "advice": "One sentence."},
  "notes": ["Practical note shown to the user"],
  "open_issues": ["Thing the user must check"],
  "sources": [{"title": "Page title", "url": "https://…"}]
}
```

Rules enforced by `scripts/plan_tool.py check`:
- `category` ∈ `venue, live-event, catering, accommodation, transport, activity`.
- Slots sorted by `date` + `start`; dates inside `date_start..date_end`
  (`end_date` may be one day after `date_end` for overnight stays); `HH:MM` times.
- **Exactly 3 candidates per slot**, ranks `1,2,3`. A slot may have fewer only if it sets
  `"shortlist_note"` explaining why (e.g. "Only 2 caterers deliver to this area").
- Every candidate: `name`, `summary`, `price.amount` ≥ 0 in the **event currency**
  (`amount` = total for the whole group), `contact.website` (https) **and at least one** of
  `contact.booking` / `phone` / `email`, and a `source` URL.
- No duplicate candidate names inside a slot. `weather` may be `null`.

## Commands

```bash
python3 .claude/skills/plan-data/scripts/plan_tool.py check   runs/<id>/artifacts/plan.json
python3 .claude/skills/plan-data/scripts/plan_tool.py to-md   runs/<id>/artifacts/plan.json <run-id> > runs/<id>/artifacts/schedule.md
python3 .claude/skills/plan-data/scripts/plan_tool.py budget  runs/<id>/artifacts/plan.json   # JSON budget summary
```
Budget is computed, never typed: per slot the cheapest, the top pick (rank 1) and the most
expensive option, plus 10 % contingency, against `budget_limit`.
