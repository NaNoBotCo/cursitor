"""Court holiday tables: computed from the rules that define them, or read from holidays/*.json.

California court holidays follow CCP §135 and Gov. Code §6700, observed as California Rules of
Court, rule 1.11 directs: a holiday on a Sunday closes the court the Monday after, a holiday on a
Saturday closes it the Friday before. Federal holidays follow 5 U.S.C. §6103.

    python3 -m cursitor deadline holidays --year 2028 --jurisdiction ca --write
"""
import datetime as _dt
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLE_DIR = os.path.join(ROOT, "holidays")

D = _dt.date


def nth_weekday(year, month, weekday, n):
    """n-th weekday (Mon=0) of a month; n=-1 is the last one."""
    if n > 0:
        first = D(year, month, 1)
        shift = (weekday - first.weekday()) % 7
        return first + _dt.timedelta(days=shift + 7 * (n - 1))
    nxt = D(year + (month // 12), month % 12 + 1, 1)
    last = nxt - _dt.timedelta(days=1)
    shift = (last.weekday() - weekday) % 7
    return last - _dt.timedelta(days=shift)


def observed(day):
    """Rule 1.11 and 5 U.S.C. §6103(b): Saturday -> Friday before, Sunday -> Monday after."""
    if day.weekday() == 5:
        return day - _dt.timedelta(days=1)
    if day.weekday() == 6:
        return day + _dt.timedelta(days=1)
    return day


def _fixed(year, month, day, name):
    actual = D(year, month, day)
    return (observed(actual), name, actual)


def _floating(day, name):
    return (day, name, day)


def ca_judicial(year):
    """California court holidays for one year: list of (closed_date, name, statutory_date)."""
    thanksgiving = nth_weekday(year, 11, 3, 4)
    rows = [
        _fixed(year, 1, 1, "New Year's Day"),
        _floating(nth_weekday(year, 1, 0, 3), "Martin Luther King Jr. Day"),
        _fixed(year, 2, 12, "Lincoln's Birthday"),
        _floating(nth_weekday(year, 2, 0, 3), "Washington's Birthday"),
        _fixed(year, 3, 31, "César Chávez Day"),
        _floating(nth_weekday(year, 5, 0, -1), "Memorial Day"),
        _fixed(year, 6, 19, "Juneteenth"),
        _fixed(year, 7, 4, "Independence Day"),
        _floating(nth_weekday(year, 9, 0, 1), "Labor Day"),
        _floating(nth_weekday(year, 9, 4, 4), "Native American Day"),
        _fixed(year, 11, 11, "Veterans Day"),
        _floating(thanksgiving, "Thanksgiving Day"),
        _floating(thanksgiving + _dt.timedelta(days=1), "Day after Thanksgiving"),
        _fixed(year, 12, 25, "Christmas Day"),
    ]
    return sorted(rows)


def federal(year):
    """Federal legal holidays for one year (5 U.S.C. §6103), with observed dates."""
    rows = [
        _fixed(year, 1, 1, "New Year's Day"),
        _floating(nth_weekday(year, 1, 0, 3), "Birthday of Martin Luther King, Jr."),
        _floating(nth_weekday(year, 2, 0, 3), "Washington's Birthday"),
        _floating(nth_weekday(year, 5, 0, -1), "Memorial Day"),
        _fixed(year, 6, 19, "Juneteenth National Independence Day"),
        _fixed(year, 7, 4, "Independence Day"),
        _floating(nth_weekday(year, 9, 0, 1), "Labor Day"),
        _floating(nth_weekday(year, 10, 0, 2), "Columbus Day"),
        _fixed(year, 11, 11, "Veterans Day"),
        _floating(nth_weekday(year, 11, 3, 4), "Thanksgiving Day"),
        _fixed(year, 12, 25, "Christmas Day"),
    ]
    return sorted(rows)


SOURCES = {
    "ca": {
        "source": "Code Civ. Proc. §135; Gov. Code §6700; Cal. Rules of Court, rule 1.11 (Sunday holiday observed Monday, Saturday holiday observed the Friday before)",
        "verify": "the court's own holiday calendar for the year; a court can close on other days by order",
        "file": "ca_judicial_{year}.json",
        "compute": ca_judicial,
    },
    "federal": {
        "source": "5 U.S.C. §6103(a)-(b); FRCP 6(a)(6)",
        "verify": "the district court's own holiday calendar; FRCP 6(a)(6) also counts days declared holidays by the President or Congress",
        "file": "federal_{year}.json",
        "compute": federal,
    },
}


def closed_in(year, jurisdiction):
    """Closed days that fall in `year`, including a Friday Dec 31 that observes the next New Year's
    Day, and leaving out a Dec 31 of the year before."""
    fn = SOURCES[jurisdiction]["compute"]
    rows = [r for r in fn(year) if r[0].year == year] + [r for r in fn(year + 1) if r[0].year == year]
    return sorted(rows)


def table(year, jurisdiction):
    """The table as a dict, ready to write as JSON."""
    meta = SOURCES[jurisdiction]
    rows = []
    for closed, name, actual in closed_in(year, jurisdiction):
        row = {"date": closed.isoformat(), "weekday": closed.strftime("%a"), "name": name}
        if closed != actual:
            row["observed_for"] = actual.isoformat()
        rows.append(row)
    return {
        "jurisdiction": jurisdiction,
        "year": year,
        "source": meta["source"],
        "verify": meta["verify"],
        "computed_by": "cursitor/holidays.py",
        "holidays": rows,
    }


def write_table(year, jurisdiction, directory=None):
    directory = directory or TABLE_DIR
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, SOURCES[jurisdiction]["file"].format(year=year))
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(table(year, jurisdiction), fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return path


_CACHE = {}


def load(year, jurisdiction, directory=None):
    """{date: name} for one year. Reads the JSON table when present (so a court's own
    corrections win), else computes it."""
    key = (year, jurisdiction, directory)
    if key in _CACHE:
        return _CACHE[key]
    directory = directory or TABLE_DIR
    path = os.path.join(directory, SOURCES[jurisdiction]["file"].format(year=year))
    out = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        for row in data.get("holidays", []):
            out[D.fromisoformat(row["date"])] = row["name"]
    else:
        for closed, name, _actual in closed_in(year, jurisdiction):
            out[closed] = name
    _CACHE[key] = out
    return out


def holiday_name(day, jurisdiction, directory=None):
    return load(day.year, jurisdiction, directory).get(day)
