---
description: "Turn text into pleading paper (California, federal) or a letter"
argument-hint: "<in.txt|md> <out.pdf> [--caption caption.json] [--format ca|federal|letter] [--signed NAME]"
---

Run `"${CLAUDE_PLUGIN_ROOT}/scripts/cursitor" plead $ARGUMENTS` with the Bash tool.

Before running it on a document for filing or service, run `"${CLAUDE_PLUGIN_ROOT}/scripts/cursitor" muzzle <in>` and `"${CLAUDE_PLUGIN_ROOT}/scripts/cursitor" gate <in>` and show the results. Without `--signed` the signature line prints blank for a wet signature. After the PDF is built, give its path as a short link (`"${CLAUDE_PLUGIN_ROOT}/scripts/cursitor" link add <out.pdf>`) and the page count.
