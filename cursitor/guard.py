"""Pre-push check: keep a matter's identifiers out of a git repository.

    cursitor guard [repo-dir] [--matter DIR]...    exit 1 and list hits when found
    cursitor guard install [repo-dir]              write .git/hooks/pre-push that runs the check

Identifiers come from each matter's matter.json: `identifiers`, `case_number` and the party
names. Without --matter, every matter registered by `new-matter` (in ~/.cursitor/matters.txt)
counts. The check reads the tracked and staged files of the repository.
"""
import json
import os
import re
import stat
import subprocess
import sys

from . import matter as _matter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def identifiers(matter_dirs):
    out = {}
    for m in matter_dirs:
        p = os.path.join(m, "matter.json")
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8") as fh:
            data = json.load(fh)
        vals = list(data.get("identifiers", []))
        if data.get("case_number"):
            vals.append(data["case_number"])
        for side in (data.get("parties") or {}).values():
            vals.extend(side)
        for v in vals:
            v = (v or "").strip()
            if len(v) >= 4:
                out[v] = m
    return out


def git_files(repo):
    def run(args):
        r = subprocess.run(["git", "-C", repo] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if r.returncode != 0:
            raise SystemExit("not a git repository: %s" % repo)
        return [x for x in r.stdout.decode("utf-8", "replace").split("\n") if x]
    files = set(run(["ls-files"])) | set(run(["diff", "--cached", "--name-only", "--diff-filter=ACMR"]))
    return sorted(files)


def scan(repo, matter_dirs):
    ids = identifiers(matter_dirs)
    if not ids:
        return [], 0
    pats = [(v, re.compile(re.escape(v).replace(r"\ ", r"[\s_-]+"), re.I)) for v in ids]
    hits = []
    files = git_files(repo)
    for rel in files:
        path = os.path.join(repo, rel)
        if not os.path.isfile(path) or os.path.getsize(path) > 5_000_000:
            continue
        for v, rx in pats:
            if rx.search(rel):
                hits.append("%s  (file name)  %r" % (rel, v))
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError:
            continue
        if b"\x00" in data[:4096]:
            text = data.decode("latin-1")
        else:
            text = data.decode("utf-8", "replace")
        for n, line in enumerate(text.split("\n"), 1):
            for v, rx in pats:
                if rx.search(line):
                    hits.append("%s:%d  %r" % (rel, n, v))
    return hits, len(files)


HOOK = """#!/bin/sh
# Written by `cursitor guard install`. Blocks a push that carries a matter's identifiers.
exec "{python}" "{cli}" guard "$(git rev-parse --show-toplevel)"
"""


def install(repo):
    gitdir = os.path.join(repo, ".git")
    if not os.path.isdir(gitdir):
        raise SystemExit("no .git folder in %s" % repo)
    hooks = os.path.join(gitdir, "hooks")
    os.makedirs(hooks, exist_ok=True)
    path = os.path.join(hooks, "pre-push")
    if os.path.exists(path):
        with open(path, encoding="utf-8", errors="replace") as fh:
            if "cursitor guard" not in fh.read():
                raise SystemExit("a pre-push hook already exists at %s; add this line to it:\n  %s"
                                 % (path, '"%s" "%s" guard "$(git rev-parse --show-toplevel)"' % (
                                     sys.executable, os.path.join(ROOT, "bin", "cursitor"))))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(HOOK.format(python=sys.executable, cli=os.path.join(ROOT, "bin", "cursitor")))
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def matters_for(args_matters):
    if args_matters:
        return [os.path.abspath(m) for m in args_matters]
    return _matter.registered()
