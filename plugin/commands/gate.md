---
description: "Read your own record before send: show every passage in served/ and received/ on the draft's subject"
argument-hint: "<draft> [matter-dir] [--read]"
---

Run `"${CLAUDE_PLUGIN_ROOT}/scripts/cursitor" gate $ARGUMENTS` with the Bash tool. Do not pass --read on the first run.

Read every passage the gate prints. Then tell the person, in plain words, which passages bear on the draft's argument: anything in their own served discovery, the other side's verified responses or the notes that supports, contradicts or strengthens a sentence in the draft, with file and line. Propose the edits that follow.

Only after the person says they have read the passages, run it again with `--read`. The draft is not cleared for service or filing until the gate prints CLEARED.
