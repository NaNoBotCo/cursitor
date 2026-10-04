---
name: calendaring
description: "Court deadlines with their arithmetic. Use whenever a date, a deadline, a hearing, a service date, a proof of service or a briefing schedule comes up in a litigation matter, in California state court or federal court."
---

# Calendaring

The engine is `"${CLAUDE_PLUGIN_ROOT}/scripts/cursitor" deadline`. It counts court days from holiday tables (California: CCP §135, Gov. Code §6700, Cal. Rules of Court, rule 1.11; federal: 5 U.S.C. §6103) and prints each date with the steps that produced it.

## A date goes out with its arithmetic

Give a deadline as the engine's one line, whole:

```
Due Wed Sep 9 2026 — served by email Aug 5 + 30 days (CCP §2030.260) = Fri Sep 4; + 2 court days e-service (§1010.6(a)(3)(B)), skipping Mon Sep 7 Labor Day = Wed Sep 9.
```

Do not compute a court deadline by hand, round it, or restate it without the steps. If the engine has no rule for the period, run `deadline from --days N` with the rule's citation in your message, and say the period came from the person, not from the rule table.

## Commands

- `deadline list` — every rule id, period and citation, and the service methods.
- `deadline from --served YYYY-MM-DD --method email --rule ca.discovery_response` — forward from service.
- `deadline back --hearing YYYY-MM-DD --rule ca.opposition` — one date counted back from a hearing.
- `deadline brief-schedule --hearing YYYY-MM-DD --rules ca` — last day to serve the motion by each method, then opposition and reply. `--rules fed.cdcal` for the Central District.
- `deadline ics calendar.json out.ics` — calendar file; hearing times in America/Los_Angeles, plus a line in the matter's `reader_tz`.
- `deadline holidays --year 2028 --jurisdiction ca --write` — writes the next year's table.
- `pos <proof-of-service.pdf>` — reads the service date and method and prints the deadlines it starts as PROPOSED. It writes to calendar.json only with `--confirm`.

## Status words

- SCHEDULED: the calendar entry's `order` names an order, notice or proof of service that is on disk.
- PROPOSED: anything else. A date someone mentioned in an email is PROPOSED.
- MOVED: only with `moved_by` naming the signed stipulation or order, on disk. `brief` flags a move without one.

## How the counting works

- California: exclude the trigger day, include the last (CCP §12); a last day on a weekend or court holiday rolls to the next court day (§12a). Mail adds 5 calendar days in California, 10 out of state, 20 out of the country (§1013(a)); overnight and e-service add 2 court days (§1013(c), §1010.6(a)(3)(B)). The extension is added to the unextended last day, then §12a applies. Counting back from a hearing excludes the hearing day (§12c); a result on a non-court day moves to the court day before.
- Federal: FRCP 6(a). Rule 6(d) adds 3 days for mail, leaving with the clerk, or other consented means, after the period would otherwise end; electronic service adds none. California state holidays (6(a)(6)(C)) appear as a note; `--state-holidays` applies them.

The holiday tables carry a `verify` field: the court's own holiday calendar is the record, and a court can close on other days by order.
