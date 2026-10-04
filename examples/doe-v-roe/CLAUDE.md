# Matter rules for Claude — Doe v. Roe Holdings (fictional example)

Boot order, every session:
1. STATUS.md — the narrative. Append-only. The last dated block wins.
2. DONE.md — the ledger. A dated line means done. A line without a date, or an unclear one, means not done.
3. calendar.json — dates. `cursitor brief` reads it.
4. forks/ — open decisions. `cursitor fork list`.

`cursitor boot` prints all four.

Working rules for this matter:
- File links: give every file as a short link from `cursitor link add <path>`, a plain path with no file:// prefix.
- Dates: a date goes out with its arithmetic, in one line. `cursitor deadline from` writes the line.
- Scheduled: an event is SCHEDULED only when an order, notice or proof of service on disk names it (the entry's `order` field). Otherwise it is PROPOSED. A date is MOVED only when the signed stipulation or order that moved it is on disk and named in `moved_by`.
- Read the record before send: before clearing any paper for service or filing, run `cursitor gate <draft>`, read every passage it prints from served/ and received/, then rerun with `--read`.
- Muzzles: muzzles.txt lists words and topics that stay off paper. `cursitor muzzle <draft>` checks a draft.
- Forks go to the person: options, cost, worst case, expiry, default if silent — written with `cursitor fork new`, decided by the person with `cursitor fork decide`. A standing instruction with no recorded decision is an open fork.
- Reader copies: anything the person reads ships as plain .txt (`cursitor txt`), one paragraph per line.
- Absence: when a document is not in this folder, say "not on this disk", not "does not exist".

