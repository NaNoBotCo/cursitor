---
description: "Fork cards: write out a decision for the person, list open ones, record a decision"
argument-hint: "new --question ... --option 'a|label|cost|worst case' --option 'b|...' --expiry YYYY-MM-DD --default a|none | list | decide F1 b --by NAME"
---

Run `"${CLAUDE_PLUGIN_ROOT}/scripts/cursitor" fork $ARGUMENTS` with the Bash tool.

A fork belongs to the person. When writing one, give each option its cost and worst case, an expiry date, and what happens if nobody answers (`--default none` when silence must not choose). Record a decision only when the person states it, with `decide <id> <choice> --by <their name>`; decisions append to forks/decisions.jsonl.
