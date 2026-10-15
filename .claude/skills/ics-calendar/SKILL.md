---
name: ics-calendar
description: Build and validate RFC 5545 iCalendar (.ics) files from plan.json — one program calendar plus one tentative calendar per shortlisted option with its booking contacts. Use for the /plan-event calendar output or whenever a plan must be exported as calendar events.
---

# iCalendar builder + validator

Nothing is booked by the workflow, so every event is `STATUS:TENTATIVE` and shown as
free time (`TRANSP:TRANSPARENT`). The user can add any option to their calendar **before**
deciding, compare in their own calendar, and delete the ones they don't book.

## What gets built (from `plan.json`, see the plan-data skill)

| File | Contents |
|------|----------|
| `program.ics` | one event per slot, titled "<slot> (to choose)", description lists all options with price and contacts |
| `<slot-id>-<rank>.ics` | one event for that option: name, address as LOCATION, booking link as URL, price + website + phone + e-mail in DESCRIPTION |

UIDs are derived from run id + slot id (+ option name), and DTSTAMP is the approval time,
so rebuilding the same plan produces identical files.

## Build

```bash
python3 .claude/skills/ics-calendar/scripts/build_ics.py \
  runs/<run-id>/artifacts/plan.json runs/<run-id>/output/calendar <run-id> <approval decided_at>
```
The output folder is cleared of old `.ics` files first.

## Validate

```bash
python3 .claude/skills/ics-calendar/scripts/validate_ics.py \
  runs/<run-id>/output/calendar --plan runs/<run-id>/artifacts/plan.json
```
Checks every file: CRLF endings, lines ≤ 75 octets, `VERSION:2.0` and `PRODID`, each VEVENT
has `UID DTSTAMP DTSTART DTEND SUMMARY` in UTC with `DTEND > DTSTART`, unique UIDs. With
`--plan`: program events = slots, exactly one calendar per option. Exit 0 = pass.

Encoding notes (handled by the builder): text escapes `\\ ; , newline`; long lines are folded
at 75 octets without splitting multi-byte characters; local times are converted to UTC from
the plan's IANA time zone, so daylight-saving changes are correct.
