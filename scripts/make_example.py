#!/usr/bin/env python3
"""Build the generated files of the fictional example matter, examples/doe-v-roe/.

    python3 scripts/make_example.py

Writes the messy pasted complaint, three exhibit PDFs (one an image-only scan, so OCR has work
to do), a proof of service and a notice of case management conference. Every name, address and
number in them is fictional.
"""
import io
import os
import random

# fixed PDF timestamps, so a rebuild changes no bytes and carries no local time zone
os.environ.setdefault("RL_invariant", "1")
import subprocess
import sys
import tempfile

from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MATTER = os.path.join(ROOT, "examples", "doe-v-roe")
sys.path.insert(0, ROOT)

from cursitor.pleading import wrap  # noqa: E402

# --------------------------------------------------------------------------- the pasted complaint

CAPTION_LINES = [
    "JANE DOE",
    "100 Sample Way, Apt. 4",
    "Oakland, CA 94600",
    "Telephone: (555) 010-0100",
    "Email: jane.doe@example.com",
    "Plaintiff in Pro Per",
    "",
    "               SUPERIOR COURT OF THE STATE OF CALIFORNIA",
    "                       COUNTY OF ALAMEDA",
    "",
    "JANE DOE,                              )  Case No. 26CV000000",
    "                                       )",
    "              Plaintiff,               )  COMPLAINT FOR DAMAGES",
    "                                       )",
    "      v.                               )  1. Breach of Lease",
    "                                       )  2. Breach of the Implied",
    "ROE HOLDINGS, LLC, a California        )     Warranty of Habitability",
    "limited liability company; and DOES   )  3. Violation of Civil Code",
    "1 through 10, inclusive,               )     section 1950.5",
    "                                       )  4. Negligence",
    "              Defendants.              )",
    "_______________________________________)  DEMAND FOR JURY TRIAL",
    "",
]

# Body: (kind, text). "~" marks a word the PDF split across a line break with a hyphen.
BODY = [
    ("p", "Plaintiff Jane Doe alleges as follows:"),
    ("h", "GENERAL ALLEGATIONS"),
    ("n", "1. Plaintiff is an individual who, at all times relevant to this complaint, resided in the City of Oakland, County of Alameda, California."),
    ("n", "2. Defendant Roe Holdings, LLC (“Roe Holdings”) is a California limited liability company that owns and manages the residential building at 100 Sample Way, Oakland, California (the “Building”)."),
    ("n", "3. Plaintiff does not know the true names of the defendants sued as Does 1 through 10 and sues them by fictitious names under Code of Civil Procedure section 474. Plaintiff will amend this complaint when their names are learned."),
    ("n", "4. On or about March 1, 2025, Plaintiff and Roe Holdings signed a written lease for Apartment 4 of the Building (the “Lease”) for a term of one year at a monthly rent of $2,150. Plaintiff paid a security deposit of $3,200. A copy of the Lease is attached as Exhibit 1."),
    ("n", "5. Paragraph 12 of the Lease provides:"),
    ("q", "Landlord shall keep the premises in a condition fit for occupancy and shall make all repairs needed to keep the roof, plumbing, heating and walls in good working order, within a reasonable time after written notice from Tenant."),
    ("n", "6. On November 18, 2025, water began entering Apartment 4 through the bathroom ceiling. Plaintiff gave Roe Holdings written notice by email that day. A copy of the email chain is attached as Exhibit 3."),
    ("n", "7. Roe Holdings did not repair the leak. By January 2026, mold covered parts of the bathroom ceiling and the bedroom wall shared with the bathroom."),
    ("n", "8. On or about March 3, 2026, an inspector from Example Air Testing Co. inspected Apartment 4 at Roe Holdings’ request and found elevated mold spore counts in the bathroom and bedroom. A copy of the inspec~tion report is attached as Exhibit 2."),
    ("n", "9. Plaintiff moved out on April 30, 2026, after the leak and mold made the bedroom unusable. Plaintiff left the apartment clean and returned the keys that day."),
    ("n", "10. Roe Holdings did not return any part of the security deposit and did not provide an itemized statement of deductions within 21 days after Plaintiff moved out, as Civil Code section 1950.5(g) requires."),
    ("h", "FIRST CAUSE OF ACTION"),
    ("c", "(Breach of Lease — Against All Defendants)"),
    ("n", "11. Plaintiff incorporates paragraphs 1 through 10."),
    ("n", "12. Plaintiff performed all conditions of the Lease required of her, except those excused by Defendants’ conduct."),
    ("n", "13. Roe Holdings breached paragraph 12 of the Lease by failing to repair the leak within a reasonable time after written notice."),
    ("n", "14. As a result, Plaintiff suffered damages, including rent paid for an apartment that was partly unusable, moving costs, and damaged personal property, in an amount to be proven at trial."),
    ("h", "SECOND CAUSE OF ACTION"),
    ("c", "(Breach of the Implied Warranty of Habitability — Against All Defendants)"),
    ("n", "15. Plaintiff incorporates paragraphs 1 through 14."),
    ("n", "16. The Lease carried an implied warranty of habit~ability. The water intrusion and mold made Apartment 4 untenant~able within the meaning of Civil Code section 1941.1 and Health and Safety Code section 17920.3."),
    ("n", "17. Roe Holdings had notice of the conditions no later than November 18, 2025, and did not correct them within a reasonable time. Plaintiff did not use repair-and-deduct self-~help under Civil Code section 1942."),
    ("n", "18. Plaintiff’s damages include the reduced rental value of Apartment 4 from November 18, 2025, through April 30, 2026."),
    ("h", "THIRD CAUSE OF ACTION"),
    ("c", "(Violation of Civil Code Section 1950.5 — Against Roe Holdings)"),
    ("n", "19. Plaintiff incorporates paragraphs 1 through 18."),
    ("n", "20. Roe Holdings kept the $3,200 security deposit without serving an itemized statement within 21 days after Plaintiff moved out."),
    ("n", "21. Roe Holdings kept the deposit in bad faith. Under Civil Code section 1950.5(l), Plaintiff seeks the deposit and statutory damages of up to twice the amount of the deposit."),
    ("h", "FOURTH CAUSE OF ACTION"),
    ("c", "(Negligence — Against All Defendants)"),
    ("n", "22. Plaintiff incorporates paragraphs 1 through 21."),
    ("n", "23. Roe Holdings owed Plaintiff a duty to use reasonable care in maintaining the Building."),
    ("n", "24. Roe Holdings breached that duty by leaving a known leak unrepaired for more than five months."),
    ("n", "25. The breach damaged Plaintiff’s furniture, clothing and a laptop computer, in an amount to be proven at trial."),
    ("h", "PRAYER FOR RELIEF"),
    ("p", "WHEREFORE, Plaintiff prays for judgment against Defendants as follows:"),
    ("n", "1. For general and special damages in an amount to be proven at trial;"),
    ("n", "2. For return of the $3,200 security deposit and statutory damages under Civil Code section 1950.5(l);"),
    ("n", "3. For costs of suit; and"),
    ("n", "4. For such other relief as the Court finds just."),
    ("h", "DEMAND FOR JURY TRIAL"),
    ("p", "Plaintiff demands a trial by jury on all causes of action so triable."),
    ("s", "Dated: May 11, 2026                    ______________________________"),
    ("s", "                                       JANE DOE"),
    ("s", "                                       Plaintiff in Pro Per"),
]

WIDTH = 66


def _wrap_plain(text, width, first_prefix="", rest_prefix=""):
    """Wrap at `width` characters; '~' forces a hyphenated break at that point."""
    segs = text.split("~")
    lines, cur, prefix = [], "", first_prefix
    for si, seg in enumerate(segs):
        for w in seg.split(" "):
            if not w:
                continue
            trial = (cur + " " + w) if cur else w
            if len(prefix) + len(trial) <= width:
                cur = trial
            else:
                lines.append(prefix + cur)
                prefix, cur = rest_prefix, w
        if si < len(segs) - 1:
            lines.append(prefix + cur + ("" if cur.endswith("-") else "-"))
            prefix, cur = rest_prefix, ""
    if cur:
        lines.append(prefix + cur)
    return lines


def body_lines():
    out = []
    for kind, text in BODY:
        if kind == "h":
            out.append(" " * ((WIDTH - len(text)) // 2) + text)
        elif kind == "c":
            for ln in _wrap_plain(text, WIDTH - 10):
                out.append(" " * ((WIDTH - len(ln)) // 2) + ln)
        elif kind == "n":
            num, rest = text.split(" ", 1)
            out.extend(_wrap_plain(rest, WIDTH, "      %-5s" % num, ""))
        elif kind == "q":
            out.extend(_wrap_plain(text, WIDTH - 10, "          ", "          "))
        elif kind == "p":
            out.extend(_wrap_plain(text, WIDTH, "      ", ""))
        elif kind == "s":
            out.append(text)
    return out


def pasted_complaint():
    lines = CAPTION_LINES + body_lines()
    pages = [lines[i:i + 28] for i in range(0, len(lines), 28)]
    out = []
    for pi, page in enumerate(pages, 1):
        if pi > 1:
            out.append("Doe v. Roe Holdings, LLC — Case No. 26CV000000")
            out.append("")
        for n, ln in enumerate(page, 1):
            out.append(("%2d  %s" % (n, ln)).rstrip())
        out.append("")
        out.append("- %d -" % pi)
        out.append("                         COMPLAINT FOR DAMAGES - %d" % pi)
        out.append("")
    return "\n".join(out)


# --------------------------------------------------------------------------- PDFs

def text_pdf(path, pages, title):
    c = canvas.Canvas(path, pagesize=LETTER)
    c.setTitle(title)
    c.setCreator("Cursitor example generator")
    W, H = LETTER
    for page in pages:
        y = H - 72
        for kind, text in page:
            if kind == "title":
                c.setFont("Helvetica-Bold", 15)
                c.drawCentredString(W / 2, y, text)
                y -= 26
            elif kind == "sub":
                c.setFont("Helvetica-Bold", 11)
                c.drawString(72, y, text)
                y -= 18
            elif kind == "gap":
                y -= 10
            else:
                c.setFont("Times-Roman", 11)
                for ln in wrap(text, W - 144, "Times-Roman", 11):
                    c.drawString(72, y, ln)
                    y -= 14
                y -= 6
        c.showPage()
    c.save()


LEASE = [
    [("title", "RESIDENTIAL LEASE AGREEMENT"),
     ("p", "This Residential Lease Agreement is made on March 1, 2025, between Roe Holdings, LLC, a California limited liability company (\"Landlord\"), and Jane Doe (\"Tenant\"), for Apartment 4 at 100 Sample Way, Oakland, California 94600 (the \"Premises\")."),
     ("sub", "1. Term"),
     ("p", "The term begins March 1, 2025 and ends February 28, 2026, and continues month to month after that unless either party gives written notice."),
     ("sub", "2. Rent"),
     ("p", "Tenant pays rent of $2,150 per month, due on the first day of each month, by bank transfer to the account Landlord names in writing."),
     ("sub", "3. Security Deposit"),
     ("p", "Tenant has paid a security deposit of $3,200. Landlord holds and returns the deposit as Civil Code section 1950.5 provides."),
     ("sub", "4. Use"),
     ("p", "The Premises are for residential use by Tenant only."),
     ("sub", "12. Repairs"),
     ("p", "Landlord shall keep the premises in a condition fit for occupancy and shall make all repairs needed to keep the roof, plumbing, heating and walls in good working order, within a reasonable time after written notice from Tenant."),
     ("sub", "13. Notices"),
     ("p", "Notices to Landlord go to the property manager by email at manager@roe-holdings.example or by mail to Roe Holdings, LLC, 200 Example Plaza, Suite 10, Oakland, California 94600.")],
    [("sub", "14. Entire Agreement"),
     ("p", "This Lease is the whole agreement between the parties about the Premises. Any change must be in writing and signed by both parties."),
     ("gap", ""),
     ("p", "LANDLORD: Roe Holdings, LLC    By: ______________________   Morgan Roe, Managing Member"),
     ("gap", ""),
     ("p", "TENANT: ______________________   Jane Doe"),
     ("gap", ""),
     ("p", "Fictional document generated for the Cursitor example matter.")],
]

EMAILS = [
    [("title", "EMAIL CORRESPONDENCE: WATER LEAK, APARTMENT 4"),
     ("sub", "From: Jane Doe <jane.doe@example.com>"),
     ("p", "To: manager@roe-holdings.example   Date: November 18, 2025, 7:42 a.m.   Subject: Water leak in Apartment 4"),
     ("p", "Water is coming through the bathroom ceiling of Apartment 4 this morning. It has soaked the bath mat and is dripping near the light fixture. Please send someone today. I am home all day."),
     ("sub", "From: Property Manager <manager@roe-holdings.example>"),
     ("p", "To: Jane Doe   Date: November 19, 2025, 4:15 p.m.   Subject: RE: Water leak in Apartment 4"),
     ("p", "Thanks for letting us know. Our plumber can look at it when he is next in the building."),
     ("sub", "From: Jane Doe <jane.doe@example.com>"),
     ("p", "To: manager@roe-holdings.example   Date: January 12, 2026, 9:03 p.m.   Subject: RE: Water leak in Apartment 4"),
     ("p", "No one has come. The leak continues every time the unit upstairs runs water. There is now black mold on the bathroom ceiling and on the bedroom wall. Please repair the leak as paragraph 12 of the lease requires."),
     ("p", "Fictional document generated for the Cursitor example matter.")],
]

INSPECTION = [
    "EXAMPLE AIR TESTING CO.",
    "MOLD INSPECTION REPORT",
    "",
    "Property: 100 Sample Way, Apt. 4, Oakland, CA",
    "Client: Roe Holdings, LLC",
    "Date of inspection: March 3, 2026",
    "Inspector: R. Sample, Certified Mold Inspector",
    "",
    "Findings",
    "Bathroom ceiling: visible growth, about 6 square feet.",
    "Bedroom wall shared with bathroom: visible growth,",
    "about 4 square feet; moisture reading 38 percent.",
    "Air sample, bathroom: 14,200 spores per cubic meter.",
    "Air sample, bedroom: 9,800 spores per cubic meter.",
    "Outdoor control sample: 1,100 spores per cubic meter.",
    "",
    "Conclusion",
    "Indoor spore counts exceed the outdoor control. The",
    "source is an active leak above the bathroom ceiling.",
    "Repair the leak, then remove affected drywall.",
    "",
    "Report delivered to client March 3, 2026.",
    "Fictional document generated for the Cursitor example.",
]


def _font(size):
    from PIL import ImageFont
    for cand in ("/System/Library/Fonts/Supplemental/Courier New.ttf",
                 "/System/Library/Fonts/Supplemental/Arial.ttf",
                 "/Library/Fonts/Arial.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "/usr/share/fonts/dejavu/DejaVuSans.ttf"):
        if os.path.exists(cand):
            return ImageFont.truetype(cand, size)
    return None


def scan_pdf(path, lines):
    """An image-only PDF: the page is a picture of text, with no text layer."""
    dpi = 150
    W, H = int(8.5 * dpi), int(11 * dpi)
    try:
        from PIL import Image, ImageDraw, ImageFilter
        font = _font(30)
        big = _font(38)
        if font is None:
            raise ImportError("no TrueType font")
        img = Image.new("L", (W, H), 246)
        d = ImageDraw.Draw(img)
        y = 150
        for i, ln in enumerate(lines):
            f = big if i < 2 else font
            d.text((150, y), ln, fill=25, font=f)
            y += 48 if i < 2 else 40
        rnd = random.Random(7)
        px = img.load()
        for _ in range(9000):
            x, yy = rnd.randrange(W), rnd.randrange(H)
            px[x, yy] = rnd.choice((120, 200, 230))
        img = img.rotate(0.6, fillcolor=246).filter(ImageFilter.GaussianBlur(0.5))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=55)
        jpg = os.path.join(tempfile.mkdtemp(), "scan.jpg")
        with open(jpg, "wb") as fh:
            fh.write(buf.getvalue())
    except ImportError:
        jpg = _scan_via_ghostscript(lines)
    c = canvas.Canvas(path, pagesize=LETTER)
    c.setTitle("Scanned document")
    c.drawImage(jpg, 0, 0, width=LETTER[0], height=LETTER[1])
    c.showPage()
    c.save()


def _scan_via_ghostscript(lines):
    tmp = tempfile.mkdtemp()
    src = os.path.join(tmp, "src.pdf")
    c = canvas.Canvas(src, pagesize=LETTER)
    y = LETTER[1] - 72
    for ln in lines:
        c.setFont("Courier", 14)
        c.drawString(72, y, ln)
        y -= 20
    c.save()
    jpg = os.path.join(tmp, "scan.jpg")
    subprocess.run(["gs", "-q", "-dNOPAUSE", "-dBATCH", "-sDEVICE=jpeggray", "-r150",
                    "-dJPEGQ=55", "-sOutputFile=" + jpg, src], check=True)
    return jpg


def proof_of_service(path):
    W, H = LETTER
    c = canvas.Canvas(path, pagesize=LETTER)
    c.setTitle("Proof of Service")
    y = H - 72
    rows = [
        ("b", "PROOF OF SERVICE"),
        ("t", "Jane Doe v. Roe Holdings, LLC, Alameda County Superior Court, Case No. 26CV000000"),
        ("t", ""),
        ("t", "I am over the age of 18 and not a party to this action. My business address is 200 Example Plaza, Suite 12, Oakland, California 94600. My electronic service address is service@poe-moe.example."),
        ("t", "On September 9, 2026, I served the following documents:"),
        ("t", "DEFENDANT ROE HOLDINGS, LLC'S VERIFIED RESPONSES TO SPECIAL INTERROGATORIES, SET ONE; DEFENDANT ROE HOLDINGS, LLC'S VERIFIED RESPONSES TO REQUESTS FOR PRODUCTION, SET ONE"),
        ("t", "on the interested parties in this action as follows: Jane Doe, Plaintiff in Pro Per, 100 Sample Way, Apt. 4, Oakland, CA 94600, jane.doe@example.com"),
        ("t", "[  ] BY MAIL: I placed the documents in a sealed envelope with postage fully prepaid for collection and mailing."),
        ("t", "[  ] BY PERSONAL SERVICE: I delivered the documents by hand to the person at the address above."),
        ("t", "[X] BY ELECTRONIC SERVICE: Based on a court order or an agreement of the parties to accept electronic service, I caused the documents to be sent to the person at the electronic service address listed above."),
        ("t", "I declare under penalty of perjury under the laws of the State of California that the foregoing is true and correct. Executed on September 9, 2026, at Oakland, California."),
        ("t", ""),
        ("t", "Casey Example                                   /s/ Casey Example"),
        ("t", "Fictional document generated for the Cursitor example matter."),
    ]
    for kind, text in rows:
        if kind == "b":
            c.setFont("Times-Bold", 14)
            c.drawCentredString(W / 2, y, text)
            y -= 28
            continue
        c.setFont("Times-Roman", 12)
        for ln in wrap(text, W - 144, "Times-Roman", 12):
            c.drawString(72, y, ln)
            y -= 16
        y -= 8
    c.save()


def notice_cmc(path):
    W, H = LETTER
    c = canvas.Canvas(path, pagesize=LETTER)
    c.setTitle("Notice of Case Management Conference")
    y = H - 72
    for kind, text in [
        ("b", "SUPERIOR COURT OF CALIFORNIA, COUNTY OF ALAMEDA"),
        ("b", "NOTICE OF CASE MANAGEMENT CONFERENCE"),
        ("t", "Case: Jane Doe v. Roe Holdings, LLC     Case No. 26CV000000"),
        ("t", "Date: November 12, 2026     Time: 9:00 a.m.     Department: 17"),
        ("t", "Notice is given that a Case Management Conference is set as above. Each party files a Case Management Statement (form CM-110) no later than 15 calendar days before the conference (Cal. Rules of Court, rule 3.725)."),
        ("t", "Dated: June 15, 2026        Clerk of the Court, by Deputy Clerk"),
        ("t", "Fictional document generated for the Cursitor example matter."),
    ]:
        if kind == "b":
            c.setFont("Times-Bold", 13)
            c.drawCentredString(W / 2, y, text)
            y -= 24
            continue
        c.setFont("Times-Roman", 12)
        for ln in wrap(text, W - 144, "Times-Roman", 12):
            c.drawString(72, y, ln)
            y -= 16
        y -= 8
    c.save()


def main():
    os.makedirs(os.path.join(MATTER, "paste"), exist_ok=True)
    os.makedirs(os.path.join(MATTER, "exhibits"), exist_ok=True)
    os.makedirs(os.path.join(MATTER, "received"), exist_ok=True)
    with open(os.path.join(MATTER, "paste", "complaint-pasted.txt"), "w", encoding="utf-8") as fh:
        fh.write(pasted_complaint() + "\n")
    text_pdf(os.path.join(MATTER, "exhibits", "1 Lease agreement.pdf"), LEASE, "Residential Lease Agreement")
    scan_pdf(os.path.join(MATTER, "exhibits", "2 Inspection report (scan).pdf"), INSPECTION)
    text_pdf(os.path.join(MATTER, "exhibits", "3 Email chain.pdf"), EMAILS, "Email correspondence")
    proof_of_service(os.path.join(MATTER, "received", "2026-09-09 Proof of Service of responses.pdf"))
    notice_cmc(os.path.join(MATTER, "received", "2026-06-15 Notice of Case Management Conference.pdf"))
    print("example files written under", os.path.relpath(MATTER, ROOT))


if __name__ == "__main__":
    main()
