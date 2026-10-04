"""The calendar engine: court-day counting, rule tables, and a date that carries its arithmetic.

Every result is one line: the date, then the steps that produced it, each with its citation.

    Due Wed Sep 9 2026 — served by email Aug 5 + 30 days (CCP §2030.260) = Fri Sep 4; + 2 court days
    e-service (§1010.6(a)(3)(B)), skipping Mon Sep 7 Labor Day = Wed Sep 9.
"""
import datetime as _dt
import json
import os

from . import holidays as _hol

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULE_DIR = os.path.join(ROOT, "rules")
ONE = _dt.timedelta(days=1)

JURISDICTION_FILES = {"ca": "ca.json", "fed": "federal.json", "federal": "federal.json"}


class RuleError(ValueError):
    pass


# --------------------------------------------------------------------------- formatting

def fmt(d, ref_year=None, weekday=True):
    """'Fri Sep 4' — the year is added when it differs from ref_year."""
    s = ("%s %s %d" % (d.strftime("%a"), d.strftime("%b"), d.day)) if weekday else \
        ("%s %d" % (d.strftime("%b"), d.day))
    if ref_year is not None and d.year != ref_year:
        s += " %d" % d.year
    return s


def fmt_full(d):
    return "%s %s %d %d" % (d.strftime("%a"), d.strftime("%b"), d.day, d.year)


def parse_date(s):
    if isinstance(s, _dt.date):
        return s
    try:
        return _dt.date.fromisoformat(str(s).strip())
    except ValueError:
        raise RuleError("dates are written YYYY-MM-DD; got %r" % s)


# --------------------------------------------------------------------------- the court calendar

class Court:
    """Which days a court is open. `holidays` is the table key ('ca' or 'federal')."""

    def __init__(self, holidays="ca", extra_closed=None, state_holidays=None, table_dir=None):
        self.holidays = holidays
        self.state_holidays = state_holidays
        self.extra = dict(extra_closed or {})
        self.table_dir = table_dir

    def holiday(self, d):
        name = self.extra.get(d)
        if name:
            return name
        return _hol.holiday_name(d, self.holidays, self.table_dir)

    def state_holiday(self, d):
        if not self.state_holidays:
            return None
        return _hol.holiday_name(d, self.state_holidays, self.table_dir)

    def is_court_day(self, d):
        return d.weekday() < 5 and not self.holiday(d)

    def why_closed(self, d):
        h = self.holiday(d)
        if h:
            return h
        if d.weekday() == 5:
            return "a Saturday"
        if d.weekday() == 6:
            return "a Sunday"
        return None

    def add_court_days(self, start, n):
        """Count n court days after `start` (n<0 counts before). Returns (date, named holidays skipped)."""
        step = ONE if n >= 0 else -ONE
        d, left, skipped = start, abs(n), []
        while left:
            d += step
            if self.is_court_day(d):
                left -= 1
            else:
                h = self.holiday(d)
                if h:
                    skipped.append((d, h))
        return d, skipped

    def roll(self, d, backward=False):
        """Next court day on or after d (or on or before, counting backward). Returns (date, skipped)."""
        step = -ONE if backward else ONE
        skipped = []
        while not self.is_court_day(d):
            skipped.append((d, self.why_closed(d)))
            d += step
        return d, skipped


# --------------------------------------------------------------------------- rule tables

_TABLES = {}


def load_jurisdiction(jur, rule_dir=None):
    jur = "fed" if jur in ("fed", "federal") else jur
    key = (jur, rule_dir)
    if key in _TABLES:
        return _TABLES[key]
    fname = JURISDICTION_FILES.get(jur, jur + ".json")
    path = os.path.join(rule_dir or RULE_DIR, fname)
    if not os.path.exists(path):
        raise RuleError("no rule table for %r at %s" % (jur, path))
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    data["_by_id"] = {r["id"]: r for r in data["rules"]}
    _TABLES[key] = data
    return data


def all_rules(rule_dir=None):
    out = []
    for jur in ("ca", "fed"):
        t = load_jurisdiction(jur, rule_dir)
        out.extend((t, r) for r in t["rules"])
    return out


def find_rule(rule_id, rule_dir=None):
    jur = rule_id.split(".", 1)[0]
    table = load_jurisdiction(jur, rule_dir)
    rule = table["_by_id"].get(rule_id)
    if not rule:
        raise RuleError("unknown rule %r; `cursitor deadline list` shows the rules" % rule_id)
    return table, rule


def court_for(table, state_holidays=False):
    return Court(table.get("holidays", "ca"),
                 state_holidays=table.get("state_holidays"))


def resolve_method(table, rule, method):
    if method is None:
        method = "personal"
    m = method.strip().lower().replace(" ", "-")
    m = table.get("aliases", {}).get(m, m).replace("-", "_")
    methods = rule.get("methods") or table["methods"]
    if m not in methods:
        raise RuleError("unknown service method %r for %s; choose from: %s"
                        % (method, rule["id"], ", ".join(sorted(methods))))
    return m, methods[m]


# --------------------------------------------------------------------------- results

class Result(object):
    def __init__(self, date, line, steps, rule_id, method=None, notes=None, trigger=None):
        self.date = date
        self.line = line
        self.steps = steps
        self.rule_id = rule_id
        self.method = method
        self.notes = notes or []
        self.trigger = trigger

    def as_dict(self):
        return {"date": self.date.isoformat(), "line": self.line, "rule": self.rule_id,
                "method": self.method, "notes": self.notes,
                "trigger": self.trigger.isoformat() if self.trigger else None}

    def __repr__(self):
        return "<Result %s>" % self.line


def _skips(skipped, ref_year):
    named = sorted((d, n) for d, n in skipped if n and not n.startswith("a S"))
    if not named:
        return ""
    parts = ["%s %s" % (fmt(d, ref_year), n) for d, n in named]
    return ", skipping " + (parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1])


def _roll_text(d, rolled, skipped, cite, ref_year, backward):
    first = skipped[0]
    reason = first[1]
    what = ("%s is %s" % (fmt(d, ref_year), reason)) if reason.startswith("a ") else \
           ("%s is %s, a court holiday" % (fmt(d, ref_year), reason))
    later = [(x, n) for x, n in skipped[1:] if n and not n.startswith("a S")]
    past = (", and %s" % " and ".join("%s is %s" % (fmt(x, ref_year), n) for x, n in later)) if later else ""
    verb = "moves earlier to" if backward else "rolls to"
    return "%s%s; %s %s (%s)" % (what, past, verb, fmt(rolled, ref_year), cite)


def _trigger_phrase(rule, mlabel, method_key):
    if rule.get("trigger_phrase"):
        return rule["trigger_phrase"]
    if rule.get("summons_methods"):
        return "summons served"
    return "served by %s" % mlabel


# --------------------------------------------------------------------------- forward periods

def compute(rule_id, trigger, method=None, days=None, rule_dir=None, state_holidays=False,
            prefix="Due"):
    """A deadline measured AFTER an event (service, filing, a waiver request)."""
    r = _compute(rule_id, trigger, method, days, rule_dir, state_holidays, prefix, None)
    if parse_date(trigger).year != r.date.year:
        r = _compute(rule_id, trigger, method, days, rule_dir, state_holidays, prefix, r.date.year)
    return r


def _compute(rule_id, trigger, method, days, rule_dir, state_holidays, prefix, ry):
    table, rule = find_rule(rule_id, rule_dir)
    if rule["direction"] != "after":
        raise RuleError("%s counts back from a hearing; use `deadline brief-schedule` or backward()" % rule_id)
    trigger = parse_date(trigger)
    court = court_for(table)
    cnt = table["counting"]
    n = int(days if days is not None else rule["days"])
    notes = list(filter(None, [rule.get("notes")]))
    frags = []

    # When service of a summons is complete depends on how it was made.
    start = trigger
    mkey, mlabel, method_row = None, None, None
    if rule.get("summons_methods"):
        sm = rule["summons_methods"]
        mkey = (method or "personal").lower().replace("-", "_")
        if mkey not in sm:
            raise RuleError("for %s the method is one of: %s" % (rule_id, ", ".join(sorted(sm))))
        row = sm[mkey]
        if row.get("complete_after"):
            start = trigger + _dt.timedelta(days=row["complete_after"])
            frags.append("summons mailed %s; %s (%s) = %s" % (
                fmt(trigger, ry, weekday=False), row["phrase"], row["cite"], fmt(start, ry)))
        mlabel = row["label"]
    elif rule.get("service_extension"):
        mkey, method_row = resolve_method(table, rule, method)
        mlabel = method_row["label"]
    else:
        if method:
            mkey, method_row = resolve_method(table, rule, method)
            mlabel = method_row["label"]
            method_row = None          # this rule takes no service extension
        else:
            mlabel = "personal delivery"

    if rule.get("unit") == "court":
        base, skipped = court.add_court_days(start, n)
        base_txt = "+ %d court days (%s)%s = %s" % (n, rule["cite"], _skips(skipped, ry), fmt(base, ry))
    else:
        base = start + _dt.timedelta(days=n)
        base_txt = "+ %d days (%s) = %s" % (n, rule["cite"], fmt(base, ry))

    if frags:
        frags[-1] += "; " + base_txt
    else:
        frags.append("%s %s %s" % (_trigger_phrase(rule, mlabel, mkey),
                                   fmt(trigger, ry, weekday=False), base_txt))

    d = base
    mode = cnt.get("extension_mode", "before_roll")
    add = int(method_row.get("add", 0)) if method_row else 0

    if mode == "after_roll" and add:
        rolled, sk = court.roll(d)
        if rolled != d:
            frags.append(_roll_text(d, rolled, sk, cnt["roll_cite"], ry, False))
            d = rolled

    if method_row and add:
        if method_row.get("unit") == "court":
            d2, sk = court.add_court_days(d, add)
            frags.append("+ %d court days %s (%s)%s = %s" % (
                add, method_row["short"], method_row["short_cite"], _skips(sk, ry), fmt(d2, ry)))
        else:
            d2 = d + _dt.timedelta(days=add)
            frags.append("+ %d days %s (%s) = %s" % (add, method_row["short"], method_row["short_cite"], fmt(d2, ry)))
        d = d2
    elif method_row and method_row.get("zero_note"):
        frags.append(method_row["zero_note"])

    rolled, sk = court.roll(d)
    if rolled != d:
        frags.append(_roll_text(d, rolled, sk, cnt["roll_cite"], ry, False))
        d = rolled

    # FRCP 6(a)(6)(C): a state holiday can extend a forward federal period.
    if court.state_holidays:
        sh = court.state_holiday(d)
        if sh:
            if state_holidays:
                d_old = d
                while court.state_holiday(d) or not court.is_court_day(d):
                    d += ONE
                frags.append("%s is %s, a California holiday counted under FRCP 6(a)(6)(C); runs to %s"
                             % (fmt(d_old, ry), sh, fmt(d, ry)))
            else:
                notes.append("%s is %s, a California holiday; FRCP 6(a)(6)(C) may carry the deadline to the next day. "
                             "This date does not take that extension (--state-holidays applies it)." % (fmt(d, ry), sh))

    # every intermediate date in the line is in the due date's year unless it says otherwise
    line = "%s %s — %s." % (prefix, fmt_full(d), "; ".join(frags))
    return Result(d, line, frags, rule_id, mkey, notes, trigger)


# --------------------------------------------------------------------------- backward periods

def backward(rule_id, hearing, method=None, rule_dir=None, prefix=None):
    """A deadline measured BEFORE a hearing (notice, opposition, reply)."""
    r = _backward(rule_id, hearing, method, rule_dir, prefix, None)
    if parse_date(hearing).year != r.date.year:
        r = _backward(rule_id, hearing, method, rule_dir, prefix, r.date.year)
    return r


def _backward(rule_id, hearing, method, rule_dir, prefix, ry):
    table, rule = find_rule(rule_id, rule_dir)
    if rule["direction"] != "before":
        raise RuleError("%s counts forward from an event; use compute()" % rule_id)
    hearing = parse_date(hearing)
    court = court_for(table)
    cnt = table["counting"]
    n = int(rule["days"])
    frags = []
    if rule.get("unit") == "court":
        base, skipped = court.add_court_days(hearing, -n)
        frags.append("%s %s − %d court days (%s)%s = %s" % (
            rule.get("trigger", "hearing"), fmt(hearing, ry), n, rule["cite"], _skips(skipped, ry), fmt(base, ry)))
    else:
        base = hearing - _dt.timedelta(days=n)
        frags.append("%s %s − %d days (%s) = %s" % (rule.get("trigger", "hearing"), fmt(hearing, ry), n, rule["cite"], fmt(base, ry)))
    d = base
    mkey = None
    if rule.get("service_extension"):
        mkey, mrow = resolve_method(table, rule, method)
        add = int(mrow.get("add", 0))
        if add:
            if cnt.get("extension_mode") == "after_roll":
                rolled, sk = court.roll(d, backward=True)
                if rolled != d:
                    frags.append(_roll_text(d, rolled, sk, cnt["backward_cite"], ry, True))
                    d = rolled
            if mrow.get("unit") == "court":
                d2, sk = court.add_court_days(d, -add)
                frags.append("− %d court days %s (%s)%s = %s" % (
                    add, mrow["short"], mrow["short_cite"], _skips(sk, ry), fmt(d2, ry)))
            else:
                d2 = d - _dt.timedelta(days=add)
                frags.append("− %d days %s (%s) = %s" % (add, mrow["short"], mrow["short_cite"], fmt(d2, ry)))
            d = d2
        elif mrow.get("zero_note"):
            frags.append(mrow["zero_note"])
    rolled, sk = court.roll(d, backward=True)
    if rolled != d:
        frags.append(_roll_text(d, rolled, sk, cnt["backward_cite"], ry, True))
        d = rolled
    if mkey:
        mlabel = (rule.get("methods") or table["methods"])[mkey]["label"]
        prefix = "Serve by %s no later than" % mlabel
    elif prefix is None:
        prefix = "Due"
    line = "%s %s — %s." % (prefix, fmt_full(d), "; ".join(frags))
    notes = list(filter(None, [rule.get("notes")]))
    return Result(d, line, frags, rule_id, mkey, notes, hearing)


def brief_schedule(hearing, schedule="ca", rule_dir=None):
    """Backward briefing schedule from a hearing date: list of (heading, [Result])."""
    jur = "fed" if schedule.startswith("fed") else schedule.split(".")[0]
    table = load_jurisdiction(jur, rule_dir)
    sched = table.get("schedules", {}).get(schedule)
    if not sched:
        raise RuleError("no schedule %r; known: %s" % (schedule, ", ".join(sorted(table.get("schedules", {})))))
    out = []
    for row in sched["rows"]:
        rule = table["_by_id"][row["rule"]]
        results = []
        if row.get("methods"):
            for m in row["methods"]:
                results.append(backward(row["rule"], hearing, m, rule_dir, prefix="Serve by"))
        else:
            results.append(backward(row["rule"], hearing, None, rule_dir, prefix="Due"))
        out.append((row["prefix"], rule, results))
    return sched["label"], out


def describe_rule(table, rule):
    unit = "court days" if rule.get("unit") == "court" else "days"
    when = "after" if rule["direction"] == "after" else "before"
    s = "%-28s %3d %s %s %s — %s (%s)" % (rule["id"], rule["days"], unit, when, rule["trigger"],
                                         rule["label"], rule["cite"])
    if rule.get("also"):
        s += "; also " + "; ".join(rule["also"])
    return s
