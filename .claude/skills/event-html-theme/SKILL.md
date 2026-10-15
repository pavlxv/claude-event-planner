---
name: event-html-theme
description: Predefined HTML template, partials and a renderer that populates them from plan.json to produce the /plan-event guide (event-plan.html) with a per-option add-to-calendar button. Use when rendering an approved shortlist so every run has the same structure and look.
---

# Event guide — predefined template, populated by a script

The model never writes HTML for the guide. The page is defined once:

```
template.html            page shell, all CSS, section order
partials/run-item.html   one stop in the program strip
partials/slot.html       one part of the event (time rail + its options)
partials/ticket.html     one option as a ticket; the tear-off stub holds price + calendar button
partials/weather-day.html, budget-row.html, source-item.html
example/plan.example.json  fictional plan for previewing the design
```
`scripts/render_html.py` fills `{{placeholders}}` from `plan.json` (values are HTML-escaped;
keys ending in `_html` are pre-rendered partials), drops optional blocks marked
`<!--IF:name--> … <!--ENDIF:name-->`, computes the budget with the plan-data skill, and embeds
every calendar file as a `data:text/calendar` link. Same plan in → same page out.

## Design
- **Idea:** each option is a ticket. The dashed, notched stub at the bottom is where you
  act: price and *Add to calendar*. The top pick's stub is marigold; that is the only
  strong colour on the page.
- **Palette:** paper `#F4F6F9`, surface `#FFFFFF`, ink `#18202D`, muted `#5E6979`,
  line `#D8DEE6`, cobalt `#2C57F5` (actions, links), marigold `#FFC94D` (top pick).
  Dark mode is automatic (`prefers-color-scheme`).
- **Type:** condensed grotesk for the title, times, names and prices
  (`Avenir Next Condensed` → `Roboto Condensed` → `Arial Narrow`); system sans for text;
  tabular figures for every number. No web fonts — the file must work offline.
- **Layout:** left-aligned. Hero with a large title and a four-fact strip; a program strip
  of links; then one band per part of the event — a sticky time rail on the left, up to
  three tickets on the right (stacked on phones); weather tiles; a budget meter against
  the limit and a cheapest / top pick / priciest table; notes; whole-program calendar; sources.
- **Accessibility:** visible focus rings, reduced-motion respected, prints cleanly.

Sections, in this fixed order (`data-section`): `overview`, `program`, `shortlists`,
`weather` (only if the plan has weather), `budget`, `notes` (only if notes/open issues),
`calendar`, `sources`. To change the look, edit `template.html` / partials — never the output.

## Render and check

```bash
python3 .claude/skills/event-html-theme/scripts/render_html.py \
  runs/<id>/artifacts/plan.json runs/<id>/output/calendar runs/<id>/output/event-plan.html <approval decided_at>
python3 .claude/skills/event-html-theme/scripts/check_html.py \
  runs/<id>/output/event-plan.html --plan runs/<id>/artifacts/plan.json
```
The check verifies section order, no unfilled placeholders, no external resources, no
internal workflow names, one calendar link per option + one for the program, and that the
options on the page match the plan exactly. Build the calendars first (ics-calendar skill).

Preview the design without a run:
```bash
python3 .claude/skills/ics-calendar/scripts/build_ics.py .claude/skills/event-html-theme/example/plan.example.json /tmp/cal demo 2026-10-15T09:00:00+00:00
python3 .claude/skills/event-html-theme/scripts/render_html.py .claude/skills/event-html-theme/example/plan.example.json /tmp/cal /tmp/preview.html 2026-10-15T09:00:00+00:00
```
