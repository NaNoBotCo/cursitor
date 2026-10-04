---
name: read-the-record-gate
description: "Before any paper is cleared for service, filing or sending (a letter, a motion, a reply, a declaration, discovery responses), read what the matter's own record says on its subject. Use whenever a draft is about to go out."
---

# Read the record before send

A draft argues a subject. The person's served discovery, the other side's verified answers and the notes often hold a stronger argument, or a fact that sinks a sentence. The gate puts those passages in front of you before the paper leaves.

## Steps

1. `"${CLAUDE_PLUGIN_ROOT}/scripts/cursitor" muzzle <draft>` — words and topics from `muzzles.txt` that stay off paper. Exit 1 on a hit, with line numbers.
2. `"${CLAUDE_PLUGIN_ROOT}/scripts/cursitor" gate <draft>` — the draft's subject terms, and every passage on them in `served/`, `received/` and `notes/`, with file and line. It prints BLOCKED.
3. Read every passage. Tell the person which ones bear on the draft and how: a verified answer that contradicts the other side's position, a request that already asked for the thing the draft says is missing, a note that names the stronger point. Quote file and line. Propose the edits.
4. When the person says they have read the passages, run the gate again with `--read`. It prints CLEARED and logs the draft's hash to `gate.log`.

A draft changed after clearing is a new draft: run the gate again.

## Muzzles

`muzzles.txt` holds one entry per line: a word, a name, a phrase or a regular expression, matched without regard to case. Lines starting with `#` are notes. The plugin's PostToolUse hook runs `muzzle` and `voice` on each file written under a matter's `drafts/` folder and reports hits back.

## Absence

The disk holds part of what the person has. When the gate finds nothing, say the record on this disk has nothing on the subject; do not say no such document exists.
