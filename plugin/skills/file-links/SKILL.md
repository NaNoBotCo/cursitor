---
name: file-links
description: "Give every file as a short plain path. Use whenever an answer names a file the person will open, paste or attach, especially files with long names, em-dashes, brackets or spaces."
---

# File links

Court files collect long names. A path full of em-dashes and brackets turns into percent-encoding when pasted into a browser or a chat. The link farm keeps short ASCII symlinks to the real files.

- `"${CLAUDE_PLUGIN_ROOT}/scripts/cursitor" link add <path> [short-name]` prints the short path. Give that path to the person as a plain path, without a `file://` prefix.
- `link list` shows every link as OK or DEAD. Run it before finishing a build and fix any DEAD line.
- `link mv <old> <new>` renames the real file and re-points its links in the same step. A rename without it leaves dead links.
- `link prune` removes dead links.

The farm is `~/cursitor-links/` unless `$CURSITOR_LINKS` or `--farm` says otherwise. A link is a symlink: opening it opens the real file; deleting it deletes only the link.
