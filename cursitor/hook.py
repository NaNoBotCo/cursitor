"""Claude Code hook entry points (used by plugin/hooks/hooks.json).

    cursitor hook post-write   PostToolUse on Write|Edit: muzzle + voice on files under a matter's drafts/
    cursitor hook pre-bash     PreToolUse on Bash: a `git push` runs `cursitor guard` first

Each reads the hook's JSON on stdin. Exit 2 sends the report on stderr back to Claude: after a
write it is feedback to fix; before a push it blocks the command. Any internal error exits 0.
"""
import json
import os
import re
import sys

from . import guard as _guard
from . import matter as _matter
from . import muzzle as _muzzle
from . import voice as _voice

PUSH = re.compile(r"(^|[;&|]\s*|\s)git(\s+-C\s+\S+)?\s+push\b")


def _payload():
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def post_write():
    p = _payload()
    ti = p.get("tool_input") or {}
    path = ti.get("file_path") or ""
    if not path or not os.path.isfile(path):
        return 0
    if (os.sep + "drafts" + os.sep) not in path:
        return 0
    m = _matter.find(os.path.dirname(path))
    if not m:
        return 0
    hits = _muzzle.check(path, m)
    hits += _voice.check_files([path], matter=m)
    if not hits:
        return 0
    sys.stderr.write("CURSITOR — %d hit(s) in %s:\n" % (len(hits), os.path.relpath(path, m)))
    for h in hits[:30]:
        sys.stderr.write("  " + h + "\n")
    sys.stderr.write("Muzzle hits come from muzzles.txt in the matter; voice hits from the voice lists. "
                     "Rewrite the lines, or mark a quoted line with `voice: allow`.\n")
    return 2


def pre_bash():
    p = _payload()
    cmd = (p.get("tool_input") or {}).get("command") or ""
    if not PUSH.search(cmd):
        return 0
    repo = p.get("cwd") or os.getcwd()
    m = re.search(r"git\s+-C\s+(\S+)", cmd)
    if m:
        repo = os.path.join(repo, m.group(1).strip("'\""))
    if not os.path.isdir(os.path.join(repo, ".git")) and not os.path.isfile(os.path.join(repo, ".git")):
        return 0
    extra = [x for x in os.environ.get("CURSITOR_MATTER", "").split(os.pathsep) if x]
    matters = _guard.matters_for(extra) if extra else _matter.registered()
    if not matters:
        return 0
    hits, _n = _guard.scan(repo, matters)
    if not hits:
        return 0
    sys.stderr.write("CURSITOR GUARD — push blocked: %d place(s) in tracked or staged files carry a matter's "
                     "identifiers:\n" % len(hits))
    for h in hits[:30]:
        sys.stderr.write("  " + h + "\n")
    sys.stderr.write("Remove them from the repository (and its history), then push again.\n")
    return 2


def main(which):
    try:
        return {"post-write": post_write, "pre-bash": pre_bash}[which]()
    except KeyError:
        sys.stderr.write("hook is post-write or pre-bash\n")
        return 0
    except SystemExit:
        return 0
    except Exception:
        return 0
