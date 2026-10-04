"""The calendar engine: holidays, court-day counting, rule arithmetic, backward schedules."""
import datetime as dt

from cursitor import deadlines as dl
from cursitor import holidays as hol

D = dt.date


# --------------------------------------------------------------------------- holiday tables

def test_ca_2026_court_holidays_match_the_courts_list():
    want = [D(2026, 1, 1), D(2026, 1, 19), D(2026, 2, 12), D(2026, 2, 16), D(2026, 3, 31), D(2026, 5, 25),
            D(2026, 6, 19), D(2026, 7, 3), D(2026, 9, 7), D(2026, 9, 25), D(2026, 11, 11), D(2026, 11, 26),
            D(2026, 11, 27), D(2026, 12, 25)]
    got = [r[0] for r in hol.closed_in(2026, "ca")]
    assert got == want


def test_ca_2026_table_on_disk_matches_computed():
    on_disk = sorted(hol.load(2026, "ca").keys())
    assert on_disk == [r[0] for r in hol.closed_in(2026, "ca")]


def test_table_carries_source_and_verify_fields():
    t = hol.table(2026, "ca")
    assert "rule 1.11" in t["source"] and "§135" in t["source"]
    assert t["verify"]


def test_saturday_holidays_observed_the_friday_before():
    assert hol.holiday_name(D(2026, 7, 3), "ca") == "Independence Day"      # Jul 4 2026 is a Saturday
    assert hol.holiday_name(D(2027, 6, 18), "ca") == "Juneteenth"           # Jun 19 2027 is a Saturday
    assert hol.holiday_name(D(2027, 12, 24), "ca") == "Christmas Day"       # Dec 25 2027 is a Saturday
    assert hol.holiday_name(D(2027, 12, 31), "ca") == "New Year's Day"      # Jan 1 2028 is a Saturday
    assert hol.holiday_name(D(2026, 7, 3), "federal") == "Independence Day"


def test_sunday_holiday_observed_monday():
    assert hol.holiday_name(D(2027, 7, 5), "ca") == "Independence Day"      # Jul 4 2027 is a Sunday
    assert hol.holiday_name(D(2027, 7, 4), "ca") is None


def test_rule_based_holidays():
    assert hol.nth_weekday(2026, 9, 4, 4) == D(2026, 9, 25)                 # Native American Day
    assert hol.nth_weekday(2027, 9, 4, 4) == D(2027, 9, 24)
    assert hol.nth_weekday(2026, 5, 0, -1) == D(2026, 5, 25)                # Memorial Day
    assert hol.holiday_name(D(2026, 11, 27), "ca") == "Day after Thanksgiving"
    assert hol.holiday_name(D(2026, 11, 27), "federal") is None
    assert hol.holiday_name(D(2026, 10, 12), "federal") == "Columbus Day"
    assert hol.holiday_name(D(2026, 10, 12), "ca") is None
    assert hol.holiday_name(D(2026, 3, 31), "federal") is None


# --------------------------------------------------------------------------- court days

def test_court_days_skip_weekends_and_holidays():
    c = dl.Court("ca")
    d, skipped = c.add_court_days(D(2026, 9, 4), 1)                         # Fri, then Sat Sun Labor Day
    assert d == D(2026, 9, 8)
    assert skipped == [(D(2026, 9, 7), "Labor Day")]
    d, _ = c.add_court_days(D(2026, 11, 25), 1)                             # Thanksgiving + day after
    assert d == D(2026, 11, 30)
    d, _ = c.add_court_days(D(2026, 10, 5), -9)
    assert d == D(2026, 9, 21)


def test_roll_forward_and_backward():
    c = dl.Court("ca")
    assert c.roll(D(2026, 9, 5))[0] == D(2026, 9, 8)
    assert c.roll(D(2026, 9, 5), backward=True)[0] == D(2026, 9, 4)
    assert c.roll(D(2026, 9, 8))[0] == D(2026, 9, 8)


# --------------------------------------------------------------------------- California forward rules

def test_labor_day_2026_example_exact_line():
    r = dl.compute("ca.discovery_response", "2026-08-05", "email")
    assert r.date == D(2026, 9, 9)
    assert r.line == ("Due Wed Sep 9 2026 — served by email Aug 5 + 30 days (CCP §2030.260) = Fri Sep 4; "
                      "+ 2 court days e-service (§1010.6(a)(3)(B)), skipping Mon Sep 7 Labor Day = Wed Sep 9.")


def test_ccp_12a_roll_past_weekend_and_holiday():
    r = dl.compute("ca.rog_response", "2026-08-06", "personal")
    assert r.date == D(2026, 9, 8)
    assert "Sat Sep 5 is a Saturday" in r.line
    assert "rolls to Tue Sep 8 (CCP §12a)" in r.line
    assert "Mon Sep 7 is Labor Day" in r.line


def test_mail_extensions_by_distance():
    assert dl.compute("ca.rfp_response", "2026-08-05", "mail").date == D(2026, 9, 9)          # +5
    assert dl.compute("ca.rfp_response", "2026-08-05", "mail_out_of_state").date == D(2026, 9, 14)  # +10
    assert dl.compute("ca.rfp_response", "2026-08-05", "mail_out_of_us").date == D(2026, 9, 24)     # +20


def test_mail_extension_lands_on_weekend_then_rolls():
    # Aug 7 + 30 = Sun Sep 6, + 5 = Fri Sep 11: no roll. Aug 8 + 35 = Sat Sep 12 -> Mon Sep 14.
    r = dl.compute("ca.rfa_response", "2026-08-08", "mail")
    assert r.date == D(2026, 9, 14)
    assert "+ 5 days mail within California (§1013(a)) = Sat Sep 12" in r.line


def test_overnight_adds_two_court_days():
    r = dl.compute("ca.rog_response", "2026-08-05", "overnight")
    assert r.date == D(2026, 9, 9)
    assert "(§1013(c))" in r.line


def test_motion_to_compel_further_45_days_plus_eservice():
    r = dl.compute("ca.motion_compel_further", "2026-09-09", "email")
    assert r.date == D(2026, 10, 27)
    assert "= Sat Oct 24; + 2 court days" in r.line


def test_answer_after_substituted_service():
    r = dl.compute("ca.answer", "2026-08-05", "substituted")
    assert r.date == D(2026, 9, 14)
    assert "CCP §415.20(a)" in r.line and "CCP §412.20(a)(3)" in r.line


def test_answer_takes_no_1013_extension():
    r = dl.compute("ca.answer", "2026-08-05", "personal")
    assert r.date == D(2026, 9, 4)


def test_method_aliases_and_unknown_method():
    assert dl.compute("ca.rog_response", "2026-08-05", "e-service").date == D(2026, 9, 9)
    try:
        dl.compute("ca.rog_response", "2026-08-05", "pigeon")
    except dl.RuleError as exc:
        assert "pigeon" in str(exc)
    else:
        raise AssertionError("unknown method accepted")


def test_year_shown_on_dates_in_another_year():
    r = dl.compute("ca.discovery_response", "2026-12-02", "mail")
    assert r.date == D(2027, 1, 6)
    assert "Dec 2 2026" in r.line and r.line.startswith("Due Wed Jan 6 2027")


def test_every_result_line_carries_cites():
    for rule in ("ca.rog_response", "ca.rfp_response", "ca.rfa_response", "ca.mtc_further_rfa"):
        r = dl.compute(rule, "2026-03-02", "mail")
        assert "CCP §" in r.line and "§1013(a)" in r.line and " — " in r.line


# --------------------------------------------------------------------------- federal

def test_frcp_6d_mail_adds_three_days_after_6a():
    r = dl.compute("fed.rfp_response", "2026-08-05", "mail")
    assert r.date == D(2026, 9, 8)            # Fri Sep 4 + 3 = Mon Sep 7 Labor Day -> Tue Sep 8
    assert "(FRCP 6(d))" in r.line and "FRCP 6(a)(1)(C)" in r.line


def test_frcp_6d_not_for_electronic_service():
    r = dl.compute("fed.rfp_response", "2026-08-05", "email")
    assert r.date == D(2026, 9, 4)
    assert "no added days for electronic service" in r.line


def test_frcp_6d_added_after_the_period_rolls():
    # Aug 6 + 30 = Sat Sep 5 -> rolls past Labor Day to Tue Sep 8; + 3 = Fri Sep 11
    r = dl.compute("fed.rog_response", "2026-08-06", "mail")
    assert r.date == D(2026, 9, 11)
    # California adds its extension before the roll: Aug 6 + 30 + 5 = Thu Sep 10
    assert dl.compute("ca.rog_response", "2026-08-06", "mail").date == D(2026, 9, 10)


def test_federal_answer_and_waiver():
    assert dl.compute("fed.answer", "2026-08-05").date == D(2026, 8, 26)
    r = dl.compute("fed.answer_waiver", "2026-12-01")
    assert r.date == D(2027, 2, 1)            # Sat Jan 30 rolls to Mon Feb 1
    assert dl.compute("fed.answer_waiver_foreign", "2026-12-01").date == D(2027, 3, 1)


def test_state_holiday_reported_not_taken_unless_asked():
    r = dl.compute("fed.answer", "2026-03-10")
    assert r.date == D(2026, 3, 31)
    assert any("César Chávez Day" in n for n in r.notes)
    r2 = dl.compute("fed.answer", "2026-03-10", state_holidays=True)
    assert r2.date == D(2026, 4, 1)


# --------------------------------------------------------------------------- backward

def test_backward_brief_schedule_california():
    label, rows = dl.brief_schedule("2026-10-05", "ca")
    notice = {r.method: r for r in rows[0][2]}
    assert notice["personal"].date == D(2026, 9, 10)     # 16 court days, skipping Native American Day
    assert "skipping Fri Sep 25 Native American Day" in notice["personal"].line
    assert notice["email"].date == D(2026, 9, 8)
    assert notice["overnight"].date == D(2026, 9, 8)
    assert notice["mail"].date == D(2026, 9, 4)          # Sat Sep 5 moves earlier
    assert "moves earlier to Fri Sep 4" in notice["mail"].line
    assert notice["mail_out_of_state"].date == D(2026, 8, 31)
    assert rows[1][2][0].date == D(2026, 9, 21)          # opposition, 9 court days
    assert rows[2][2][0].date == D(2026, 9, 28)          # reply, 5 court days


def test_backward_federal_cdcal_moves_earlier_over_labor_day():
    label, rows = dl.brief_schedule("2026-10-05", "fed.cdcal")
    ecf = rows[0][2][0]
    assert ecf.date == D(2026, 9, 4)
    assert "FRCP 6(a)(5)" in ecf.line
    assert rows[1][2][0].date == D(2026, 9, 14)
    assert rows[2][2][0].date == D(2026, 9, 21)


def test_cmc_statement_counts_back_calendar_days():
    r = dl.backward("ca.cmc_statement", "2026-11-12")
    assert r.date == D(2026, 10, 28)
    assert "rule 3.725" in r.line


def test_rule_list_covers_requested_rules():
    ids = {r["id"] for _t, r in dl.all_rules()}
    for want in ("ca.discovery_response", "ca.motion_compel_further", "ca.answer", "ca.motion_notice",
                 "ca.opposition", "ca.reply", "fed.answer", "fed.answer_waiver", "fed.discovery_response",
                 "fed.rog_response", "fed.rfp_response", "fed.rfa_response"):
        assert want in ids
    for _t, r in dl.all_rules():
        assert r.get("cite"), r["id"]


def test_backward_over_thanksgiving_and_veterans_day():
    r = dl.backward("ca.motion_notice", "2026-12-03", "personal")
    assert r.date == D(2026, 11, 6)
    assert "skipping Wed Nov 11 Veterans Day, Thu Nov 26 Thanksgiving Day and Fri Nov 27 Day after Thanksgiving" in r.line
    mail = dl.backward("ca.motion_notice", "2026-12-03", "mail")
    assert mail.date == D(2026, 10, 30)          # Sun Nov 1 moves earlier to Fri Oct 30


def test_holiday_tables_for_2027_on_disk():
    assert hol.load(2027, "ca")[D(2027, 9, 24)] == "Native American Day"
    assert hol.load(2027, "federal")[D(2027, 10, 11)] == "Columbus Day"
