---
description: "Morning brief: due today, next 7 days, clocks running, proposed, flagged"
argument-hint: "[matter-dir] [--today YYYY-MM-DD]"
---

Run `"${CLAUDE_PLUGIN_ROOT}/scripts/cursitor" brief $ARGUMENTS` with the Bash tool.

Relay the brief as printed. Keep each date line whole: the date and its arithmetic stay together. List FLAGGED items first if any exist. When matter.json has a docket_url the brief checks CourtListener; exit code 2 means new docket entries, 1 means the feed could not be read.
