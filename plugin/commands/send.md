---
description: "Pick a recent output: show it in Finder, copy its path, or open a Mail draft with it attached"
argument-hint: "[matter-dir] [N] [--reveal|--copy|--mail] [--list]"
---

Run `"${CLAUDE_PLUGIN_ROOT}/scripts/cursitor" send $ARGUMENTS --list` with the Bash tool first and show the numbered list. When the person picks a number and an action, run `"${CLAUDE_PLUGIN_ROOT}/scripts/cursitor" send <N> --reveal`, `--copy` or `--mail`. `--mail` opens a Mail message with the file attached; the person addresses it and presses Send.
