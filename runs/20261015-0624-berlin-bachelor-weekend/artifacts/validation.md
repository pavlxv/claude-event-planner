# Validation: Berlin bachelor weekend

- Artifact: validation
- Owner: validator
- Run: 20261015-0624-berlin-bachelor-weekend
- Revision: 3

## Summary
Overall: PASS

All gates pass for the current artifacts (venue r2, live-events r2, weather r1, logistics r3, budget r3). Catering was dropped by the user, so G4 is N/A. Changed links were re-fetched and are reachable and relevant. Warnings are listed under Open issues.

## Details

### Gate results
| Gate | Result | Owner step | Finding |
|------|--------|------------|---------|
| G0 | PASS | - | Structural check passes for all 7 artifacts. |
| G1 | PASS | budget | Arithmetic correct. Cheapest 1214.00 + 10 % = 1335.40, top pick 1902.12, priciest 2492.60, all within 3500 EUR. |
| G2 | PASS | venue | #1 Uber Platz (arena 17,000), #2 Union stadium (about 22,000), #3 Olympiastadion (73,779) are all at least 8 guests. |
| G3 | PASS | venue | No accessibility or facility must-haves stated; accessibility pages exist for #1 and #3. |
| G4 | N/A | catering | Catering skipped (dinner dropped by the user). |
| G5 | PASS | - | All venue, show and hotel options are in Berlin, Germany. |
| G6 | PASS | - | SDP 5 Dec 19:30, Union v HSV 5 Dec, Konzerthaus 5 Dec, hotels 4-6 Dec; all inside 2026-12-04..06. |
| G7 | PASS | - | Fetched and relevant: uber-platz.de, uber-arena.de, SDP event page (5 Dec 19:30, from 79.90 EUR), fc-union-berlin.de/en (names the HSV match on 5 Dec), Union ticket shop (via redirect), ticket-compare Union v HSV page, olympiastadion.berlin/en and /contact/ (phone, e-mail), konzerthaus.de, Songkick Konzerthaus 5 Dec, Indigo and Hampton (Berlin.de), Goldmarie (HRS), uber-platz.de/kontakt. |
| G8 | PASS | venue | Outdoor, high weather risk: #2 Union and #3 Olympiastadion each name an indoor fallback (bars in Köpenick / Charlottenburg); #1 is indoor. Weather also gives an indoor-concert alternative. |
| G9 | PASS | - | Venue, live-events and logistics (hotels) each have exactly 3 options. |
| G10 | PASS | - | Every option has a website and a booking URL, phone or e-mail; nothing claims to be booked. |

## Sources
- None (validation checks workflow artifacts and the links they list)

## Open issues
- Warning: the Union club site now shows a 15:30 kick-off for Union v HSV on 5 Dec (marked as a suggested date), but venue and live-events say kick-off TBD. 15:30 is afternoon, not the evening the group asked for. Reconcile it.
- Warning: the live-events #2 Website is a third-party resale page (ticket-compare), not an official page; the price is a resale estimate. The Konzerthaus Book link is Songkick, not a ticket seller.
- Warning: requirements r2 still lists dinner as a must-have and needs_catering as yes; update it.
- Warning: the Hampton phone and e-mail and the Goldmarie phone are unconfirmed. The Uber Platz contact page phone (+49 30 20 60 70 80) differs from the ticket hotline; both are listed correctly in venue.
- Warning: the venue Book link for the Union ticket shop redirects (302) but resolves to the official shop. Hotel prices are indicative and the SDP price is a "from" price.
