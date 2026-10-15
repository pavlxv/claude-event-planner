# Weather: Berlin, 4–6 Dec 2026

- Artifact: weather
- Owner: weather-planner
- Run: 20261015-0624-berlin-bachelor-weekend
- Revision: 1

## Summary
The dates are about 50 days ahead, beyond the 16-day forecast range, so this outlook uses climatology: the same calendar dates (4–6 Dec) in each of 2021–2025 from the Open-Meteo historical archive (ERA5 reanalysis). Expect cold, damp days around 0 to 4 °C. Rain fell on at least 1 mm on 3 of 5 years for Saturday and for Sunday, so an indoor fallback is needed for the outdoor parts: the outdoor football match, outdoor transfers and walking on Saturday and Sunday. The concert and dinner are indoor and low risk. Friday arrival is mainly a frost-risk item.

## Details

### Outlook
Location: Berlin, DE (52.52437, 13.41053; timezone Europe/Berlin). Values are 5-year averages for 2021–2025. Rainy years = years with at least 1 mm precipitation that day. Gusts show the 5-year average of the daily maximum, with the highest single year in brackets.

| Date | Min °C | Max °C | Rain probability or rainy years | Wind gusts km/h | Method |
|------|-------:|-------:|---------------------------------|-----------------|--------|
| Fri 2026-12-04 | -0.5 | 2.6 | 1 of 5 years (2021: 3.5 mm) | 29.9 (max 41.8) | Climatology, 2021–2025 archive |
| Sat 2026-12-05 | 0.3 | 2.6 | 3 of 5 years (2021, 2022, 2025) | 29.8 (max 38.2) | Climatology, 2021–2025 archive |
| Sun 2026-12-06 | 0.2 | 3.4 | 3 of 5 years (2022, 2023, 2024; 2024: 9.4 mm) | 28.5 (max 39.6) | Climatology, 2021–2025 archive |

Notes: on Friday 3 of 5 years had a minimum at or below 0 °C (2022: -0.5 °C, 2023: -5.2 °C, 2025: -0.4 °C). Average precipitation is 0.7 mm on Friday, 2.1 mm on Saturday and 2.6 mm on Sunday, so Sunday is the wettest of the three days on average, mainly because of the 9.4 mm day in 2024.

### Risk assessment
Rule: high if rain probability is at least 50 % (at least 3 of 5 years), or gusts at least 50 km/h, or max at least 32 °C, or min at or below 0 °C. Ratings use the 5-year averages for temperature and the 5-year rain count; no year reached 50 km/h gusts.

| Program part | Date | Risk | Rule triggered | Indoor fallback |
|--------------|------|------|----------------|-----------------|
| Arrival transfers and walking from station or airport to hotel | Fri 2026-12-04 | high | min ≤ 0 °C (5-yr average -0.5 °C) | Indoor fallback required: use covered transport (taxi or U-Bahn/S-Bahn) instead of walking |
| Saturday evening football match (outdoor stadium) | Sat 2026-12-05 | high | rain on 3 of 5 years | Indoor fallback required: choose the indoor concert option, or a covered-stand match ticket with a wet-weather plan |
| Saturday concert (indoor venue) | Sat 2026-12-05 | low | indoor venue; only the walk to it is weather-exposed | None needed beyond the transfer rule below |
| Saturday outdoor transfers and walking between hotel, dinner and venue | Sat 2026-12-05 | high | rain on 3 of 5 years | Indoor fallback required: book taxis or public transport for each leg; keep the dinner venue within a short covered route |
| Dinner (indoor restaurant) | Sat 2026-12-05 | low | indoor; no outdoor element | None |
| Sunday departure transfer to airport or station | Sun 2026-12-06 | high | rain on 3 of 5 years | Indoor fallback required: pre-book a taxi or transfer rather than walking or using a bike |

Outcome: indoor fallback is required for the Saturday football match (if chosen), all outdoor transfers and walking on Friday, Saturday and Sunday. The concert and dinner do not need a fallback.

## Sources
- [Open-Meteo Historical Weather API documentation](https://open-meteo.com/en/docs/historical-weather-api) — daily 2021–2025 values for 4–6 Dec (ERA5 reanalysis)
- [Open-Meteo API documentation](https://open-meteo.com/en/docs) — method choice (forecast up to 16 days, archive for later dates) and variable definitions
- [Open-Meteo Geocoding API documentation](https://open-meteo.com/en/docs/geocoding-api) — resolved Berlin, DE to 52.52437, 13.41053

## Open issues
- Climatology is not a forecast. Re-check the forecast within 16 days of 4 Dec 2026 (from about 18 Nov 2026) and update the risk ratings.
- Arrival and departure times are not known, so the transfer rows assume daytime.
