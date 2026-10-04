---
description: "Compute a deadline with its arithmetic, or a backward briefing schedule"
argument-hint: "from --served YYYY-MM-DD --method email --rule ca.discovery_response | brief-schedule --hearing YYYY-MM-DD --rules ca | list"
---

Run `"${CLAUDE_PLUGIN_ROOT}/scripts/cursitor" deadline $ARGUMENTS` with the Bash tool.

With no arguments, run `"${CLAUDE_PLUGIN_ROOT}/scripts/cursitor" deadline list` first and pick the rule and method from the person's description, then show the command you ran.

Give every date exactly as the engine prints it: one line, the date followed by its arithmetic and citations. A date without its arithmetic is not a deadline. Do not round, restate or recompute the date by hand. Pass on any `Note:` lines. A computed deadline is PROPOSED until an order, notice or proof of service on disk names it.
