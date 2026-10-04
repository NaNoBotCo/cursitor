"""Fork cards: a decision that belongs to the person, written out so they can make it.

    cursitor fork new --question "..." --option "a|label|cost|worst case" --option "b|..."
                      --expiry 2026-10-27 --default a [--matter DIR]
    cursitor fork list [--all]
    cursitor fork decide F1 b --by "Jane Doe"

Each card is forks/<id>.json. A decision is one line appended to forks/decisions.jsonl; the card
file itself does not change, so the record of who decided what, and when, only grows.
"""
import datetime as _dt
import json
import os


def _dir(matter):
    d = os.path.join(matter, "forks")
    os.makedirs(d, exist_ok=True)
    return d


def cards(matter):
    d = _dir(matter)
    out = []
    for f in sorted(os.listdir(d)):
        if f.endswith(".json"):
            with open(os.path.join(d, f), encoding="utf-8") as fh:
                out.append(json.load(fh))
    out.sort(key=lambda c: (int(c["id"][1:]) if c["id"][1:].isdigit() else 9999, c["id"]))
    return out


def decisions(matter):
    p = os.path.join(_dir(matter), "decisions.jsonl")
    if not os.path.exists(p):
        return []
    out = []
    with open(p, encoding="utf-8") as fh:
        for ln in fh:
            if ln.strip():
                out.append(json.loads(ln))
    return out


def status(matter):
    """[(card, last decision or None)]"""
    last = {}
    for d in decisions(matter):
        last[d["id"]] = d
    return [(c, last.get(c["id"])) for c in cards(matter)]


def parse_option(s):
    parts = [p.strip() for p in s.split("|")]
    while len(parts) < 4:
        parts.append("")
    return {"key": parts[0], "label": parts[1], "cost": parts[2], "worst_case": parts[3]}


def new(matter, question, options, expiry=None, default=None, context="", fork_id=None):
    if len(options) < 2:
        raise SystemExit("a fork has at least two options")
    keys = [o["key"] for o in options]
    if default and default not in keys and default != "none":
        raise SystemExit("--default must be one of the option keys (%s) or 'none'" % ", ".join(keys))
    have = [c["id"] for c in cards(matter)]
    if not fork_id:
        n = 1
        while "F%d" % n in have:
            n += 1
        fork_id = "F%d" % n
    card = {
        "id": fork_id,
        "question": question,
        "context": context,
        "options": options,
        "expiry": expiry or "",
        "default_if_silent": default or "none",
        "opened": _dt.date.today().isoformat(),
    }
    with open(os.path.join(_dir(matter), fork_id + ".json"), "w", encoding="utf-8") as fh:
        json.dump(card, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return card


def decide(matter, fork_id, choice, by, note=""):
    ids = {c["id"]: c for c in cards(matter)}
    if fork_id not in ids:
        raise SystemExit("no fork %s in %s" % (fork_id, os.path.join(matter, "forks")))
    keys = [o["key"] for o in ids[fork_id]["options"]]
    if choice not in keys:
        raise SystemExit("choice must be one of: %s" % ", ".join(keys))
    if not by:
        raise SystemExit("--by names the person who decided")
    row = {"id": fork_id, "choice": choice, "by": by, "at": _dt.datetime.now().isoformat(timespec="seconds"),
           "note": note}
    with open(os.path.join(_dir(matter), "decisions.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def render_card(card, decision=None, today=None):
    today = today or _dt.date.today()
    lines = ["%s  %s" % (card["id"], card["question"])]
    if card.get("context"):
        lines.append("    " + card["context"])
    for o in card["options"]:
        lines.append("    (%s) %s — cost: %s — worst case: %s" % (o["key"], o["label"], o["cost"] or "not stated",
                                                               o["worst_case"] or "not stated"))
    exp = card.get("expiry")
    if exp:
        days = (_dt.date.fromisoformat(exp) - today).days
        lines.append("    Expires %s (%s)." % (exp, ("%d days from today" % days) if days >= 0 else "%d days ago" % -days))
    d = card.get("default_if_silent", "none")
    lines.append("    If silent: %s." % ("no default — this one is yours" if d in ("none", "") else
                                         "option (%s) by %s" % (d, exp or "the expiry")))
    if decision:
        lines.append("    DECIDED: (%s) by %s at %s%s" % (decision["choice"], decision["by"], decision["at"],
                                                         (" — " + decision["note"]) if decision.get("note") else ""))
    return "\n".join(lines)
