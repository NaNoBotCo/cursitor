---
description: "Print the matter's boot order: STATUS, DONE, calendar, open forks"
argument-hint: "[matter-dir]"
---

Run `"${CLAUDE_PLUGIN_ROOT}/scripts/cursitor" boot $ARGUMENTS` with the Bash tool from the matter folder (or pass the folder).

Read the output in full before doing anything else in this session. Then report, in a few lines:
- the current state from the last STATUS.md block;
- the next three dates, each exactly as the engine printed it (date and arithmetic in one line), with its SCHEDULED or PROPOSED status;
- every FLAG line;
- the open forks by id, question and expiry.

A date the output does not carry is not on this disk; say so rather than supplying one.
