/* Cursitor demo page. Text CC BY 4.0, code MIT. */
(function () {
'use strict';
const $ = s => document.querySelector(s);
const el = (tag, attrs, html) => { const e = document.createElement(tag); if (attrs) for (const k in attrs) e.setAttribute(k, attrs[k]); if (html != null) e.innerHTML = html; return e; };
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const store = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} } };
const dl = (blob, a) => { if (a.href) URL.revokeObjectURL(a.href); a.href = URL.createObjectURL(blob); a.hidden = false; };

/* ---------- language ---------- */
function setLang(l) {
  document.documentElement.dataset.lang = l;
  document.documentElement.lang = l;
  document.querySelectorAll('[data-set-lang]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.setLang === l)));
  store.set('cursitor-lang', l);
  renderBrief();
}
document.querySelectorAll('[data-set-lang]').forEach(b => b.addEventListener('click', () => setLang(b.dataset.setLang)));
const TH = () => document.documentElement.dataset.lang === 'th';

/* hero margin numbers */
$('#sheetnums').innerHTML = Array.from({ length: 28 }, (_, i) => i + 1).join('<br>');

/* ======================================================================
   01 PASTE — clean a pasted lawsuit, set it on pleading paper
   ====================================================================== */
const SAMPLE = [
' 1   JANE DOE',
' 2   1420 Alder Street, Apt. 3',
' 3   Oakland, CA 94607',
' 4   jane.doe@example.com',
' 5   Plaintiff in Pro Per',
' 6',
' 7',
' 8                SUPERIOR COURT OF THE STATE OF CALIFORNIA',
' 9                          COUNTY OF ALAMEDA',
'10',
'11   JANE DOE,                           )  Case No. 26CV000000',
'12                                       )',
'13               Plaintiff,              )  COMPLAINT FOR DAMAGES',
'14                                       )  (1) Breach of Warranty of',
'15         v.                            )  Habitability; (2) Negligence',
'16                                       )',
'17   ROE HOLDINGS, LLC, and DOES 1       )',
'18   through 10,                         )',
'19                                       )',
'20               Defendants.             )',
'21   ____________________________________)',
'22',
'23         Plaintiff Jane Doe alleges:',
'24                         GENERAL ALLEGATIONS',
'25         1.   Plaintiff has rented Apartment 3 at 1420 Alder Street,',
'26   Oakland, California (the "Premises") from Defendant Roe Hold-',
'27   ings, LLC ("Roe") since March 1, 2024, under a written lease.',
'28         2.   Roe owns and manages the Premises. Plaintiff does not',
'                        COMPLAINT FOR DAMAGES - 1',
'',
'Case No. 26CV000000',
' 1   know the true names of Does 1 through 10 and sues them by',
' 2   those fictitious names.',
' 3         3.   Beginning in January 2026, water entered the Premises',
' 4   through the roof each time it rained, soaking the bedroom',
' 5   ceiling and leaving visible mold on the north wall.',
' 6         4.   Plaintiff gave Roe written notice of the leak on Jan-',
' 7   uary 12, 2026, and again on February 3, 2026. On June 2,',
' 8   2026, Roe wrote that the roof "will be repaired by July 1."',
' 9   No repair was made by that date.',
'10                        FIRST CAUSE OF ACTION',
'11            (Breach of Warranty of Habitability — Against All',
'12                             Defendants)',
'13         5.   Plaintiff incorporates paragraphs 1 through 4.',
'14         6.   The leak and mold made the Premises untenantable',
'15   within the meaning of Civil Code section 1941.1.',
'16         7.   Plaintiff paid full rent throughout and has been dam-',
'17   aged in an amount to be proven at trial.',
'18                        SECOND CAUSE OF ACTION',
'19                  (Negligence — Against All Defendants)',
'20         8.   Plaintiff incorporates paragraphs 1 through 7.',
'21         9.   Roe owed Plaintiff a duty to maintain the roof with',
'22   reasonable care, breached that duty, and caused Plaintiff\'s',
'23   damages, including ruined furniture and medical visits.',
'24                              PRAYER',
'25         Plaintiff prays for damages according to proof, costs of',
'26   suit, and such other relief as the Court finds proper.',
'27',
'28   Dated: October 4, 2026          ______________________________',
'                                     JANE DOE, Plaintiff in Pro Per',
'                        COMPLAINT FOR DAMAGES - 2'
].join('\n');

const CAPTION = {
  party: 'JANE DOE\n1420 Alder Street, Apt. 3\nOakland, CA 94607\njane.doe@example.com\nPlaintiff in Pro Per',
  court: 'SUPERIOR COURT OF THE STATE OF CALIFORNIA',
  county: 'COUNTY OF ALAMEDA',
  caseNo: '26CV000000',
  parties: 'JANE DOE,\n\n          Plaintiff,\n\n     v.\n\nROE HOLDINGS, LLC, and DOES 1\nthrough 10,\n\n          Defendants.',
  title: 'COMPLAINT FOR DAMAGES\n\n(1) Breach of Warranty of\nHabitability; (2) Negligence'
};

function pasteClean(raw) {
  const st = { nums: 0, furniture: 0, hyph: 0, joins: 0, paras: 0 };
  const src = raw.replace(/\r\n?/g, '\n').replace(/\f/g, '\n').replace(/\u00a0/g, ' ').replace(/\t/g, '    ').split('\n');
  // pass 1: strip margin numbers, mark furniture
  const L = [];
  const NUM = /^\s{0,6}([1-9]|1\d|2[0-8])(?=\s|$)(?!\s*\.)/;
  const filled = src.filter(l => l.trim()).length || 1;
  const numbered = src.filter(l => NUM.test(l)).length / filled > 0.3;
  for (const line of src) {
    let t = line.replace(/\s+$/, '');
    const m = numbered ? t.match(NUM) : null;
    if (m) { t = t.slice(m[0].length).replace(/^ {1,3}/, ''); st.nums++; }
    const trimmed = t.trim();
    const furniture =
      /^[A-Z][A-Z0-9 ,.'’&()\/\-]{3,}\s+[-–—]\s*\d+\s*$/.test(trimmed) ||           // COMPLAINT FOR DAMAGES - 2
      /^[-–—]?\s*\d{1,3}\s*[-–—]?$/.test(trimmed) && !m ||                          // -2-  or 2
      /^page\s+\d+(\s+of\s+\d+)?$/i.test(trimmed) ||
      /^case\s+no\.?\s*[\w\-:]+$/i.test(trimmed) && !/\)/.test(t) ||                 // running header
      /^\/\/\/+$/.test(trimmed);                                                     // pleading filler
    if (furniture) { st.furniture++; L.push({ k: 'F' }); continue; }
    if (!trimmed) { L.push({ k: 'B' }); continue; }
    L.push({ k: 'T', t, ind: t.length - t.replace(/^\s+/, '').length, s: trimmed });
  }
  // double-spaced extraction: single blanks are soft
  const body = L.filter(x => x.k !== 'F');
  const blanks = body.filter(x => x.k === 'B').length;
  const doubleSpaced = body.length > 20 && blanks / body.length > 0.38;
  // pass 2: collapse runs of blank/furniture
  const R = [];
  for (let i = 0; i < L.length; i++) {
    if (L[i].k === 'T') { R.push(L[i]); continue; }
    let j = i, hasF = false, nb = 0;
    while (j < L.length && L[j].k !== 'T') { if (L[j].k === 'F') hasF = true; else nb++; j++; }
    if (!hasF && !(doubleSpaced && nb === 1)) R.push({ k: 'B' });
    i = j - 1;
  }
  // caption: through the last line carrying a ")" column in the first 45 lines
  let capEnd = -1;
  for (let i = 0; i < Math.min(R.length, 45); i++) if (R[i].k === 'T' && /\s{3,}\)(\s|$)|_{6,}\)/.test(R[i].t)) capEnd = i;
  const blocks = [];
  if (capEnd >= 0) {
    const cap = R.slice(0, capEnd + 1).map(x => x.k === 'T' ? x.t : '');
    const minInd = Math.min(...R.slice(0, capEnd + 1).filter(x => x.k === 'T').map(x => x.ind));
    blocks.push({ type: 'caption', lines: cap.map(s => s.slice(minInd)) });
  }
  // pass 3: paragraphs
  const isCaps = s => /[A-Z]{3}/.test(s) && !/[a-z]/.test(s) && s.length < 80;
  const isNum = s => /^(\d{1,3}|[IVXLC]{1,6}|[A-Z])\.\s|^¶\s?\d|^\(\w{1,4}\)\s/.test(s);
  let cur = null;
  const flush = () => { if (cur) { blocks.push(cur); cur = null; } };
  for (let i = capEnd + 1; i < R.length; i++) {
    const x = R[i];
    if (x.k === 'B') { flush(); continue; }
    const s = x.s;
    if (/^dated:/i.test(s)) {
      flush();
      const parts = s.split(/\s{3,}/);
      cur = { type: 'sig', lines: parts };
      while (i + 1 < R.length && R[i + 1].k === 'T' && R[i + 1].ind >= 20) { cur.lines.push(R[++i].s); }
      flush(); continue;
    }
    const centered = x.ind >= 12 && s.length < 70;
    if (isCaps(s) || (centered && /^\(/.test(s))) {
      flush();
      let h = s;
      if (/^\(/.test(s) && !/\)$/.test(s)) {
        while (i + 1 < R.length && R[i + 1].k === 'T' && R[i + 1].ind >= 12) { h += ' ' + R[++i].s; st.joins++; if (/\)$/.test(h)) break; }
      }
      blocks.push({ type: 'heading', text: h.replace(/\s{2,}/g, ' ') });
      continue;
    }
    const startsNew = isNum(s) || (x.ind >= 4 && !cur) || (x.ind >= 4 && cur && x.ind > 3 && R[i - 1] && R[i - 1].k === 'T' && R[i - 1].ind < 4 && /[.:;]$/.test(cur.text));
    if (!cur || startsNew) { flush(); cur = { type: 'para', text: s.replace(/\s{2,}/g, ' '), indent: x.ind >= 4 || isNum(s) }; continue; }
    if (/[a-z]-$/.test(cur.text) && /^[a-z]/.test(s)) { cur.text = cur.text.slice(0, -1) + s.replace(/\s{2,}/g, ' '); st.hyph++; }
    else cur.text += ' ' + s.replace(/\s{2,}/g, ' ');
    st.joins++;
  }
  flush();
  st.paras = blocks.filter(b => b.type === 'para').length;
  return { blocks, st };
}

function blocksToText(blocks) {
  return blocks.map(b => {
    if (b.type === 'caption') return b.lines.join('\n').replace(/\n{3,}/g, '\n\n');
    if (b.type === 'heading') return b.text;
    if (b.type === 'sig') return b.lines.join('\n');
    return b.text.replace(/^(\d{1,3}\.)\s+/, '$1 ');
  }).join('\n\n');
}

let lastBlocks = [];
function runPaste() {
  const { blocks, st } = pasteClean($('#pasteIn').value);
  lastBlocks = blocks;
  $('#pasteOut').value = blocksToText(blocks);
  const chip = (n, en, th) => `<span class="chip${n ? ' ok' : ''}">${n} <span class="en">${en}</span><span class="th">${th}</span></span>`;
  $('#pasteStats').innerHTML = chip(st.nums, 'line numbers removed', 'เลขบรรทัดที่ลบ') + chip(st.furniture, 'headers and footers removed', 'หัวท้ายกระดาษที่ลบ') + chip(st.hyph, 'hyphenations mended', 'คำที่ต่อแล้ว') + chip(st.joins, 'lines rejoined', 'บรรทัดที่ต่อกัน') + chip(st.paras, 'paragraphs', 'ย่อหน้า');
}
function fillCaption() {
  $('#capParty').value = CAPTION.party; $('#capCourt').value = CAPTION.court; $('#capCounty').value = CAPTION.county;
  $('#capCase').value = CAPTION.caseNo; $('#capParties').value = CAPTION.parties; $('#capTitle').value = CAPTION.title;
}
$('#pasteIn').value = SAMPLE; fillCaption(); runPaste();
let pasteTimer; $('#pasteIn').addEventListener('input', () => { clearTimeout(pasteTimer); pasteTimer = setTimeout(runPaste, 200); });
$('#pasteReset').addEventListener('click', () => { $('#pasteIn').value = SAMPLE; fillCaption(); runPaste(); });

/* WinAnsi-safe text for the standard PDF fonts */
const WINANSI = /[^\x20-\x7E\xA0-\xFF\u2018\u2019\u201A\u201C\u201D\u201E\u2013\u2014\u2026\u2022\u2020\u2021\u2030\u2039\u203A\u20AC\u2122\u0152\u0153\u0160\u0161\u0178\u017D\u017E\u0192\u02C6\u02DC]/g;
const safe = s => String(s).replace(/\u2212/g, '-').replace(WINANSI, '?');

function wrapText(text, font, size, width, firstIndent) {
  const words = safe(text).split(/\s+/).filter(Boolean), lines = []; let cur = '', w = width - (firstIndent || 0);
  for (const wd of words) {
    const t = cur ? cur + ' ' + wd : wd;
    if (font.widthOfTextAtSize(t, size) <= w || !cur) cur = t;
    else { lines.push(cur); cur = wd; w = width; }
  }
  if (cur) lines.push(cur);
  return lines.length ? lines : [''];
}

async function buildPleading(blocks, cap) {
  const { PDFDocument, StandardFonts, rgb } = PDFLib;
  const doc = await PDFDocument.create();
  doc.setTitle(cap.title.split('\n')[0]); doc.setCreator('Cursitor');
  const F = await doc.embedFont(StandardFonts.TimesRoman), B = await doc.embedFont(StandardFonts.TimesRomanBold);
  const W = 612, H = 792, TOP = 66, LEAD = 24, N = 28, R1 = 90, R2 = 97.2, BX = 104.4, RX = 540, NUMX = 84, PX = 316, CX = 328, S = 12;
  const footer = safe(cap.title.split('\n')[0]);
  const ink = rgb(0, 0, 0);
  let page = null, line = 1, pageno = 0, pending = true;
  const y = l => H - TOP - (l - 1) * LEAD;
  function newPage() {
    page = doc.addPage([W, H]); pageno++; line = 1;
    const yt = H - TOP + 14, yb = H - TOP - (N - 1) * LEAD - 10;
    page.drawLine({ start: { x: R1, y: yb }, end: { x: R1, y: yt }, thickness: 0.7, color: ink });
    page.drawLine({ start: { x: R2, y: yb }, end: { x: R2, y: yt }, thickness: 0.7, color: ink });
    for (let i = 1; i <= N; i++) { const s = String(i); page.drawText(s, { x: NUMX - F.widthOfTextAtSize(s, S), y: y(i), size: S, font: F }); }
    page.drawLine({ start: { x: BX, y: 58 }, end: { x: RX, y: 58 }, thickness: 0.5, color: ink });
    const pn = String(pageno);
    page.drawText(pn, { x: W / 2 - F.widthOfTextAtSize(pn, 10) / 2, y: 44, size: 10, font: F });
    page.drawText(footer, { x: W / 2 - F.widthOfTextAtSize(footer, 10) / 2, y: 30, size: 10, font: F });
  }
  const ensure = () => { if (pending) { pending = false; newPage(); } };
  const adv = (n = 1) => { line += n; if (line > N) { pending = true; line = 1; } };
  const need = n => { if (!pending && line + n - 1 > N) { pending = true; line = 1; } };
  const put = (t, o = {}) => {
    ensure(); const f = o.bold ? B : F; t = safe(t);
    let x = o.x != null ? o.x : BX;
    if (o.center) x = BX + (RX - BX) / 2 - f.widthOfTextAtSize(t, S) / 2;
    page.drawText(t, { x, y: y(line), size: S, font: f });
    if (o.advance !== false) adv();
  };
  // caption
  const party = cap.party.split('\n');
  party.forEach(t => put(t));
  while (line < 8) adv();
  put(cap.court, { center: true }); put(cap.county, { center: true }); adv();
  const left = cap.parties.split('\n'), right = ['Case No. ' + cap.caseNo, ''].concat(cap.title.split('\n'));
  const rows = Math.max(left.length, right.length);
  for (let r = 0; r < rows; r++) {
    ensure();
    if (left[r]) page.drawText(safe(left[r]), { x: BX, y: y(line), size: S, font: F });
    page.drawText(')', { x: PX, y: y(line), size: S, font: F });
    if (right[r]) page.drawText(safe(right[r]), { x: CX, y: y(line), size: S, font: r >= 2 ? B : F });
    adv();
  }
  ensure();
  page.drawLine({ start: { x: BX, y: y(line) + 16 }, end: { x: PX + 4, y: y(line) + 16 }, thickness: 0.6, color: ink });
  page.drawText(')', { x: PX, y: y(line) + 18 - LEAD + 6, size: S, font: F });
  adv();
  // body
  const width = RX - BX;
  for (const b of blocks) {
    if (b.type === 'caption') continue;
    if (b.type === 'heading') {
      const ls = wrapText(b.text, B, S, width - 40);
      need(ls.length + 2); ls.forEach(t => put(t, { bold: true, center: true }));
    } else if (b.type === 'sig') {
      need(b.lines.length + 2);
      put(b.lines[0]); adv();
      b.lines.slice(1).forEach(t => put(t, { x: CX }));
    } else {
      const ind = b.indent ? 36 : 0;
      const ls = wrapText(b.text, F, S, width, ind);
      if (ls.length <= 4) need(ls.length); else need(2);
      ls.forEach((t, i) => put(t, { x: BX + (i === 0 ? ind : 0) }));
    }
  }
  return { bytes: await doc.save(), pages: pageno };
}

/* pdf.js rendering */
if (window.pdfjsLib) pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
async function renderPreview(bytes, box, max = 6) {
  box.innerHTML = '';
  if (!window.pdfjsLib) return;
  const pdf = await pdfjsLib.getDocument({ data: bytes.slice() }).promise;
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  for (let p = 1; p <= Math.min(pdf.numPages, max); p++) {
    const pg = await pdf.getPage(p), vp0 = pg.getViewport({ scale: 1 }), scale = (300 * dpr) / vp0.width, vp = pg.getViewport({ scale });
    const c = el('canvas', { width: Math.round(vp.width), height: Math.round(vp.height), 'aria-label': 'Page ' + p });
    box.appendChild(c);
    await pg.render({ canvasContext: c.getContext('2d'), viewport: vp }).promise;
  }
}

$('#pleadBtn').addEventListener('click', async () => {
  const msg = $('#pleadMsg');
  if (!window.PDFLib) { msg.textContent = 'PDF library did not load; check the connection.'; return; }
  msg.textContent = '…';
  try {
    const cap = { party: $('#capParty').value, court: $('#capCourt').value, county: $('#capCounty').value, caseNo: $('#capCase').value, parties: $('#capParties').value, title: $('#capTitle').value };
    const { bytes, pages } = await buildPleading(lastBlocks, cap);
    dl(new Blob([bytes], { type: 'application/pdf' }), $('#pleadDl'));
    msg.textContent = TH() ? `${pages} หน้า กระดาษคำฟ้อง 28 บรรทัด` : `${pages} pages, 28-line pleading paper`;
    await renderPreview(bytes, $('#pleadPrev'));
  } catch (e) { msg.textContent = 'Error: ' + e.message; }
});

/* ======================================================================
   02 EXHIBITS — slip sheets, Bates, OCR, index, ask
   ====================================================================== */
let exFiles = [];
const exList = $('#exList'), drop = $('#drop'), picker = $('#exFiles');
function drawList() {
  exList.innerHTML = '';
  exFiles.forEach((f, i) => {
    const li = el('li');
    li.innerHTML = `<span class="ex">${i + 1}</span><span class="nm">${esc(f.name)}</span>`;
    const up = el('button', { type: 'button', 'aria-label': 'Move up' }, '↑'), dn = el('button', { type: 'button', 'aria-label': 'Move down' }, '↓'), rm = el('button', { type: 'button', 'aria-label': 'Remove' }, '×');
    up.onclick = () => { if (i) { [exFiles[i - 1], exFiles[i]] = [exFiles[i], exFiles[i - 1]]; drawList(); } };
    dn.onclick = () => { if (i < exFiles.length - 1) { [exFiles[i + 1], exFiles[i]] = [exFiles[i], exFiles[i + 1]]; drawList(); } };
    rm.onclick = () => { exFiles.splice(i, 1); drawList(); };
    li.append(up, dn, rm); exList.appendChild(li);
  });
  $('#exBuild').disabled = !exFiles.length;
}
async function addFiles(list) {
  for (const f of list) if (/pdf$/i.test(f.type) || /\.pdf$/i.test(f.name)) exFiles.push({ name: f.name, bytes: new Uint8Array(await f.arrayBuffer()) });
  exFiles.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));
  drawList();
}
drop.addEventListener('click', () => picker.click());
drop.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); picker.click(); } });
picker.addEventListener('change', () => addFiles(picker.files));
['dragenter', 'dragover'].forEach(t => drop.addEventListener(t, e => { e.preventDefault(); drop.classList.add('over'); }));
['dragleave', 'drop'].forEach(t => drop.addEventListener(t, e => { e.preventDefault(); drop.classList.remove('over'); }));
drop.addEventListener('drop', e => addFiles(e.dataTransfer.files));

async function textPdf(title, paras, pagesBreak) {
  const { PDFDocument, StandardFonts } = PDFLib;
  const d = await PDFDocument.create(), F = await d.embedFont(StandardFonts.TimesRoman), B = await d.embedFont(StandardFonts.TimesRomanBold);
  let p = d.addPage([612, 792]), yy = 720;
  const tw = B.widthOfTextAtSize(title, 15); p.drawText(title, { x: 306 - tw / 2, y: yy, size: 15, font: B }); yy -= 36;
  paras.forEach((t, i) => {
    if (pagesBreak && i === pagesBreak) { p = d.addPage([612, 792]); yy = 720; }
    wrapText(t, F, 12, 468).forEach(l => { p.drawText(l, { x: 72, y: yy, size: 12, font: F }); yy -= 17; });
    yy -= 10;
  });
  return d.save();
}
async function scanPdf() {
  const c = document.createElement('canvas'); c.width = 1275; c.height = 1650; const g = c.getContext('2d');
  g.fillStyle = '#f2ecdc'; g.fillRect(0, 0, c.width, c.height);
  g.save(); g.translate(40, 20); g.rotate(0.012);
  g.fillStyle = '#26221c';
  const lines = [['bold 44px Georgia', 'ROE HOLDINGS, LLC'], ['30px Georgia', '88 Harbor Way, Oakland, CA 94607'], ['30px Georgia', ''], ['30px Georgia', 'June 2, 2026'], ['30px Georgia', ''], ['30px Georgia', 'Ms. Jane Doe'], ['30px Georgia', '1420 Alder Street, Apt. 3'], ['30px Georgia', 'Oakland, CA 94607'], ['30px Georgia', ''], ['30px Georgia', 'Dear Ms. Doe:'], ['30px Georgia', ''], ['30px Georgia', 'Thank you for your letters of January 12 and February 3.'], ['30px Georgia', 'The roof over Apartment 3 will be repaired by July 1.'], ['30px Georgia', 'Our roofer, Bayline Roofing, inspected on May 28.'], ['30px Georgia', 'Please allow access on the morning of June 20.'], ['30px Georgia', ''], ['30px Georgia', 'Sincerely,'], ['30px Georgia', ''], ['italic 34px Georgia', 'R. Roe'], ['30px Georgia', 'R. Roe, Manager']];
  let yy = 180; lines.forEach(([f, t]) => { g.font = f; g.fillText(t, 150, yy); yy += 52; });
  g.restore();
  for (let i = 0; i < 2600; i++) { g.fillStyle = `rgba(40,30,20,${Math.random() * 0.25})`; g.fillRect(Math.random() * c.width, Math.random() * c.height, 1 + Math.random() * 2, 1 + Math.random() * 2); }
  const jpg = await new Promise(r => c.toBlob(r, 'image/jpeg', 0.72));
  const { PDFDocument } = PDFLib; const d = await PDFDocument.create();
  const img = await d.embedJpg(new Uint8Array(await jpg.arrayBuffer()));
  d.addPage([612, 792]).drawImage(img, { x: 0, y: 0, width: 612, height: 792 });
  return d.save();
}
$('#exSample').addEventListener('click', async () => {
  if (!window.PDFLib) return;
  $('#exMsg').textContent = '…';
  const lease = await textPdf('RESIDENTIAL LEASE AGREEMENT', [
    'This Lease is made March 1, 2024, between Roe Holdings, LLC ("Landlord") and Jane Doe ("Tenant") for Apartment 3, 1420 Alder Street, Oakland, California.',
    '1. Term. Month to month, beginning March 1, 2024.', '2. Rent. $2,150 per month, due on the first day of each month.',
    '3. Repairs. Landlord shall keep the roof, walls and plumbing in good repair and shall make repairs within a reasonable time after written notice from Tenant.',
    '4. Notices. Notices to Landlord go to 88 Harbor Way, Oakland, CA 94607.',
    '5. Entry. Landlord may enter on 24 hours written notice to make repairs.', '6. Entire agreement. This Lease is the entire agreement of the parties.',
    'Signed: Roe Holdings, LLC, by R. Roe, Manager. Jane Doe, Tenant.'], 4);
  const inv = await textPdf('BAYLINE ROOFING CO. - INVOICE No. 4471', [
    'Date: June 18, 2026. Customer: Roe Holdings, LLC, 88 Harbor Way, Oakland.', 'Job site: 1420 Alder Street, Oakland. Inspection of roof leak over Apartment 3, performed May 28, 2026.',
    'Findings: failed flashing at north parapet; saturated decking, approx. 140 sq ft; active leak path to bedroom ceiling below.',
    'Estimate for repair: $8,450. Inspection fee: $350. Amount due: $350.', 'Repair not scheduled. Awaiting owner authorization as of June 30, 2026.']);
  exFiles = [{ name: '01 Lease (signed) — Mar 2024.pdf', bytes: lease }, { name: '02 scan_0042.pdf', bytes: await scanPdf() }, { name: '03 Bayline invoice 4471.pdf', bytes: inv }];
  drawList(); $('#exMsg').textContent = '';
});

let tessP = null;
function loadTesseract() {
  if (!tessP) tessP = new Promise((res, rej) => { const s = document.createElement('script'); s.src = 'https://cdn.jsdelivr.net/npm/tesseract.js@5.1.1/dist/tesseract.min.js'; s.onload = res; s.onerror = () => rej(new Error('OCR library did not load')); document.head.appendChild(s); });
  return tessP;
}
let tessWorker = null;
async function ocrCanvas(canvas, onp) {
  await loadTesseract();
  if (!tessWorker) tessWorker = await Tesseract.createWorker('eng', 1, { logger: m => { if (m.status && onp) onp(m); } });
  const { data } = await tessWorker.recognize(canvas, {}, { text: true, blocks: true });
  let words = data.words;
  if (!words && data.blocks) { words = []; data.blocks.forEach(b => (b.paragraphs || []).forEach(p => (p.lines || []).forEach(l => (l.words || []).forEach(w => words.push(w))))); }
  return { text: data.text || '', words: words || [] };
}
function pageLines(tc) {
  let s = ''; tc.items.forEach(it => { s += it.str; s += it.hasEOL ? '\n' : (it.str && !/\s$/.test(it.str) ? ' ' : ''); });
  return s.replace(/[ \t]+\n/g, '\n');
}

let exPages = [];
$('#exBuild').addEventListener('click', async () => {
  const msg = $('#exMsg'), btn = $('#exBuild');
  if (!window.PDFLib || !window.pdfjsLib) { msg.textContent = 'PDF libraries did not load; check the connection.'; return; }
  btn.disabled = true; exPages = [];
  const prefix = ($('#exPrefix').value || 'EX').toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 8) || 'EX';
  const { PDFDocument, StandardFonts, rgb } = PDFLib;
  try {
    const out = await PDFDocument.create(); out.setTitle('Exhibits'); out.setCreator('Cursitor');
    const F = await out.embedFont(StandardFonts.TimesRoman), B = await out.embedFont(StandardFonts.TimesRomanBold), HB = await out.embedFont(StandardFonts.HelveticaBold);
    let bates = 1; const idx = [];
    for (let i = 0; i < exFiles.length; i++) {
      const f = exFiles[i], n = i + 1;
      msg.textContent = (TH() ? 'กำลังอ่าน ' : 'Reading ') + f.name;
      const pdf = await pdfjsLib.getDocument({ data: f.bytes.slice() }).promise;
      const texts = [], ocrd = [];
      for (let p = 1; p <= pdf.numPages; p++) {
        const pg = await pdf.getPage(p); let t = pageLines(await pg.getTextContent());
        if (t.replace(/\s/g, '').length < 25) {
          const vp = pg.getViewport({ scale: 2 }), c = document.createElement('canvas'); c.width = vp.width; c.height = vp.height;
          await pg.render({ canvasContext: c.getContext('2d'), viewport: vp }).promise;
          msg.textContent = (TH() ? 'OCR หน้า ' : 'OCR, page ') + p + ' · ' + f.name;
          const r = await ocrCanvas(c, m => { if (m.progress != null && m.status === 'recognizing text') msg.textContent = `OCR ${Math.round(m.progress * 100)}% · ${f.name}`; else if (m.status) msg.textContent = 'OCR: ' + m.status; });
          t = r.text; ocrd.push({ p, words: r.words, scale: 2 });
        }
        texts.push(t);
      }
      const title = ((texts[0] || '').split('\n').map(s => s.trim()).find(s => /[A-Za-z]{3}/.test(s)) || f.name).slice(0, 72);
      // slip sheet
      const slip = out.addPage([612, 792]), lab = 'EXHIBIT ' + n;
      slip.drawText(lab, { x: 306 - B.widthOfTextAtSize(lab, 40) / 2, y: 420, size: 40, font: B });
      const st = safe(title); slip.drawText(st, { x: 306 - F.widthOfTextAtSize(st, 13) / 2, y: 384, size: 13, font: F, color: rgb(0.3, 0.3, 0.3) });
      // pages
      const src = await PDFDocument.load(f.bytes, { ignoreEncryption: true });
      const copied = await out.copyPages(src, src.getPageIndices());
      const first = bates;
      copied.forEach((pg, k) => {
        out.addPage(pg);
        const { width, height } = pg.getSize();
        const o = ocrd.find(x => x.p === k + 1);
        if (o) o.words.forEach(w => {
          const bb = w.bbox; if (!bb || !w.text || !w.text.trim()) return;
          const size = Math.max(4, (bb.y1 - bb.y0) / o.scale * 0.85);
          try { pg.drawText(safe(w.text), { x: bb.x0 / o.scale, y: height - bb.y1 / o.scale + size * 0.15, size, font: F, opacity: 0 }); } catch (e) {}
        });
        const label = prefix + String(bates).padStart(6, '0'), lw = HB.widthOfTextAtSize(label, 10);
        pg.drawRectangle({ x: width - 40 - lw, y: 16, width: lw + 12, height: 16, color: rgb(1, 1, 1) });
        pg.drawText(label, { x: width - 34 - lw, y: 20.5, size: 10, font: HB });
        exPages.push({ ex: n, title, bates: label, page: k + 1, of: copied.length, text: texts[k] || '' });
        bates++;
      });
      const last = bates - 1, rng = prefix + String(first).padStart(6, '0') + (last > first ? '–' + prefix + String(last).padStart(6, '0') : '');
      idx.push({ n, title, rng, pages: copied.length, ocr: ocrd.length, file: f.name });
    }
    const bytes = await out.save();
    const lines = ['EXHIBIT INDEX', 'Doe v. Roe Holdings, LLC (fictional)', ''];
    idx.forEach(r => lines.push(`Exhibit ${r.n} · ${r.title} · ${r.rng} · ${r.pages} page${r.pages > 1 ? 's' : ''}${r.ocr ? ` · OCR ${r.ocr} page${r.ocr > 1 ? 's' : ''}` : ''} · from "${r.file}"`));
    const txt = lines.join('\n');
    $('#exIndex').textContent = txt; $('#exIndex').hidden = false;
    dl(new Blob([bytes], { type: 'application/pdf' }), $('#exDl'));
    dl(new Blob([txt + '\n'], { type: 'text/plain' }), $('#exIdx'));
    msg.textContent = TH() ? `${exFiles.length} เอกสารแนบ · ${bates - 1} หน้ามีเลข Bates` : `${exFiles.length} exhibits · ${bates - 1} Bates-stamped pages`;
    $('#askBox').hidden = false;
    if (!$('#askQ').value) $('#askQ').value = 'roof repaired by July';
    await renderPreview(bytes, $('#exPrev'), 8);
  } catch (e) { msg.textContent = 'Error: ' + e.message; }
  btn.disabled = false;
});

const STOP = new Set('the a an of to and or in on for by at is was be what when who where how did does do with from that this it as'.split(' '));
function ask() {
  const q = $('#askQ').value.toLowerCase(), terms = q.split(/[^a-z0-9$]+/).filter(t => t && !STOP.has(t));
  const box = $('#askHits'); box.innerHTML = '';
  if (!terms.length) return;
  const scored = exPages.map(p => {
    const lo = p.text.toLowerCase(); let score = 0; terms.forEach(t => { const m = lo.split(t).length - 1; score += m ? 1 + Math.min(m, 3) * 0.2 : 0; });
    return { p, score };
  }).filter(x => x.score > 0).sort((a, b) => b.score - a.score).slice(0, 4);
  if (!scored.length) { box.innerHTML = `<li>${TH() ? 'ไม่พบในชุดเอกสารนี้' : 'Not in this package.'}</li>`; return; }
  scored.forEach(({ p }) => {
    const flat = p.text.replace(/\s+/g, ' '), lo = flat.toLowerCase();
    let at = -1; for (const t of terms) { at = lo.indexOf(t); if (at >= 0) break; }
    const s = Math.max(0, at - 90), snip = (s ? '…' : '') + flat.slice(s, s + 240) + (s + 240 < flat.length ? '…' : '');
    let h = esc(snip); terms.forEach(t => { h = h.replace(new RegExp('(' + t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi'), '<mark>$1</mark>'); });
    box.appendChild(el('li', null, `<b>Exhibit ${p.ex} · ${p.bates} · ${TH() ? 'หน้า' : 'page'} ${p.page}/${p.of}</b>${h}`));
  });
}
$('#askGo').addEventListener('click', ask);
$('#askQ').addEventListener('keydown', e => { if (e.key === 'Enter') ask(); });

/* ======================================================================
   03 CALENDAR — court days, holidays, arithmetic
   ====================================================================== */
const DAY = 864e5, D = (y, m, d) => Date.UTC(y, m - 1, d), add = (t, n) => t + n * DAY, dow = t => new Date(t).getUTCDay();
const WD = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'], MO = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const fmt = (t, yr = true) => { const d = new Date(t); return `${WD[d.getUTCDay()]} ${MO[d.getUTCMonth()]} ${d.getUTCDate()}${yr ? ', ' + d.getUTCFullYear() : ''}`; };
const parseD = s => { const [y, m, d] = s.split('-').map(Number); return D(y, m, d); };
const ymd = t => new Date(t).toISOString().slice(0, 10);
function nth(y, m, wd, n) { let t = D(y, m, 1); while (dow(t) !== wd) t = add(t, 1); return add(t, 7 * (n - 1)); }
function lastWd(y, m, wd) { let t = D(y, m + 1, 0); while (dow(t) !== wd) t = add(t, -1); return t; }
const obs = t => dow(t) === 6 ? add(t, -1) : dow(t) === 0 ? add(t, 1) : t;   // CRC 1.11; 5 U.S.C. §6103(b)
function caYear(y) {
  const tg = nth(y, 11, 4, 4);
  return [[obs(D(y, 1, 1)), "New Year's Day"], [nth(y, 1, 1, 3), 'Martin Luther King Jr. Day'], [obs(D(y, 2, 12)), 'Lincoln Day'], [nth(y, 2, 1, 3), "Presidents' Day"], [obs(D(y, 3, 31)), 'César Chávez Day'], [lastWd(y, 5, 1), 'Memorial Day'], [obs(D(y, 6, 19)), 'Juneteenth'], [obs(D(y, 7, 4)), 'Independence Day'], [nth(y, 9, 1, 1), 'Labor Day'], [nth(y, 9, 5, 4), 'Native American Day'], [obs(D(y, 11, 11)), 'Veterans Day'], [tg, 'Thanksgiving'], [add(tg, 1), 'Day after Thanksgiving'], [obs(D(y, 12, 25)), 'Christmas']];
}
function fedYear(y) {
  return [[obs(D(y, 1, 1)), "New Year's Day"], [nth(y, 1, 1, 3), 'Martin Luther King Jr. Day'], [nth(y, 2, 1, 3), "Washington's Birthday"], [lastWd(y, 5, 1), 'Memorial Day'], [obs(D(y, 6, 19)), 'Juneteenth'], [obs(D(y, 7, 4)), 'Independence Day'], [nth(y, 9, 1, 1), 'Labor Day'], [nth(y, 10, 1, 2), 'Columbus Day'], [obs(D(y, 11, 11)), 'Veterans Day'], [nth(y, 11, 4, 4), 'Thanksgiving'], [obs(D(y, 12, 25)), 'Christmas']];
}
const HOL = { ca: new Map(), fed: new Map() };
for (let y = 2024; y <= 2031; y++) { caYear(y).forEach(([t, n]) => HOL.ca.set(t, n)); fedYear(y).forEach(([t, n]) => HOL.fed.set(t, n)); }
const courtDay = (t, c) => dow(t) !== 0 && dow(t) !== 6 && !HOL[c].has(t);
const why = (t, c) => HOL[c].get(t) || (dow(t) === 6 ? 'Saturday' : 'Sunday');
const skipList = (ts, c) => ts.map(t => `${fmt(t, false)}${HOL[c].has(t) ? ' ' + HOL[c].get(t) : ''}`).join(', ');

const RULES = {
  ca: [
    { id: 'disc', en: 'Responses to interrogatories, document requests or RFAs', th: 'คำตอบคำถามเป็นหนังสือ คำขอเอกสาร หรือคำขอให้รับ', days: 30, cite: 'CCP §§2030.260(a), 2031.260(a), 2033.250(a)', methods: ['personal', 'email', 'mail', 'mailout', 'mailintl', 'overnight', 'fax'] },
    { id: 'mtcf', en: 'Motion to compel further responses (from service of the responses)', th: 'คำร้องขอให้ตอบเพิ่ม (นับจากวันส่งคำตอบ)', days: 45, cite: 'CCP §§2030.300(c), 2031.310(c), 2033.290(c)', methods: ['personal', 'email', 'mail', 'mailout', 'mailintl', 'overnight', 'fax'] },
    { id: 'ans', en: 'Response to complaint (summons served)', th: 'คำให้การต่อคำฟ้อง (นับจากวันส่งหมายเรียก)', days: 30, cite: 'CCP §412.20(a)(3)', methods: ['summons', 'substituted'] }
  ],
  fed: [
    { id: 'disc', en: 'Responses to interrogatories, document requests or RFAs', th: 'คำตอบคำถามเป็นหนังสือ คำขอเอกสาร หรือคำขอให้รับ', days: 30, cite: 'FRCP 33(b)(2), 34(b)(2)(A), 36(a)(3)', methods: ['fpersonal', 'fecf', 'fmail', 'fclerk', 'fother'] },
    { id: 'ans', en: 'Answer (summons served)', th: 'คำให้การ (นับจากวันส่งหมายเรียก)', days: 21, cite: 'FRCP 12(a)(1)(A)(i)', methods: ['fsummons'] },
    { id: 'waiver', en: 'Answer after a waiver request sent within the U.S.', th: 'คำให้การหลังส่งคำขอสละการส่งหมาย (ในสหรัฐ)', days: 60, cite: 'FRCP 12(a)(1)(A)(ii)', methods: ['fwaiver'] }
  ]
};
const METHODS = {
  personal: { en: 'Personal delivery', th: 'ส่งด้วยมือ', cal: 0, court: 0 },
  email: { en: 'Electronic service (email)', th: 'ส่งทางอิเล็กทรอนิกส์ (อีเมล)', court: 2, cite: 'CCP §1010.6(a)(3)(B)', label: 'e-service' },
  mail: { en: 'Mail, within California', th: 'ไปรษณีย์ ภายในแคลิฟอร์เนีย', cal: 5, cite: 'CCP §1013(a)', label: 'mail within California' },
  mailout: { en: 'Mail, outside California', th: 'ไปรษณีย์ นอกแคลิฟอร์เนีย', cal: 10, cite: 'CCP §1013(a)', label: 'mail outside California' },
  mailintl: { en: 'Mail, outside the U.S.', th: 'ไปรษณีย์ นอกสหรัฐ', cal: 20, cite: 'CCP §1013(a)', label: 'mail outside the U.S.' },
  overnight: { en: 'Overnight delivery', th: 'จัดส่งข้ามคืน', court: 2, cite: 'CCP §1013(c)', label: 'overnight delivery' },
  fax: { en: 'Fax', th: 'แฟกซ์', court: 2, cite: 'CCP §1013(e)', label: 'fax' },
  summons: { en: 'Summons, personal delivery', th: 'หมายเรียก ส่งด้วยมือ', cal: 0, note: 'Service complete on delivery (CCP §415.10); §1013 extensions do not apply to a summons.' },
  substituted: { en: 'Summons, substituted service', th: 'หมายเรียก ส่งแทน', cal: 10, cite: 'CCP §415.20', label: 'substituted service, complete 10 days after mailing', base: 'Date mailed' },
  fpersonal: { en: 'Personal delivery', th: 'ส่งด้วยมือ', cal: 0 },
  fecf: { en: 'Electronic (CM/ECF, or email by consent)', th: 'อิเล็กทรอนิกส์ (CM/ECF หรืออีเมลโดยยินยอม)', cal: 0, note: 'No 3 days for electronic service since the 2016 amendment to FRCP 6(d).' },
  fmail: { en: 'Mail', th: 'ไปรษณีย์', f3: true, label: 'mail' },
  fclerk: { en: 'Leaving with the clerk', th: 'ฝากไว้กับเสมียนศาล', f3: true, label: 'leaving with the clerk' },
  fother: { en: 'Other means, by consent', th: 'วิธีอื่นโดยยินยอม', f3: true, label: 'other consented means' },
  fsummons: { en: 'Summons served', th: 'ส่งหมายเรียกแล้ว', cal: 0, note: 'Rule 6(d) does not add days to a summons.' },
  fwaiver: { en: 'Waiver request sent', th: 'ส่งคำขอสละการส่งหมาย', cal: 0 }
};

function rollFwd(t, c, steps, ruleCite) {
  const sk = []; while (!courtDay(t, c)) { sk.push(t); t = add(t, 1); }
  if (sk.length) steps.push({ t: `${fmt(sk[0], false)} is ${HOL[c].has(sk[0]) ? HOL[c].get(sk[0]) : 'a ' + why(sk[0], c)}; roll to the next court day${sk.length > 1 ? ', past ' + skipList(sk.slice(1), c) : ''} = ${fmt(t, false)}`, cite: ruleCite });
  return { t, sk };
}
function compute(court, rule, mid, served) {
  const m = METHODS[mid], steps = []; let t = add(served, rule.days), arith;
  steps.push({ t: `${fmt(served, false)} + ${rule.days} days = ${fmt(t, false)} (first day excluded, last included)`, cite: (court === 'ca' ? 'CCP §12; ' : 'FRCP 6(a)(1); ') + rule.cite });
  const parts = [`${fmt(served, false)} + ${rule.days} days (${rule.cite}) = ${fmt(t, false)}`];
  if (court === 'ca') {
    if (m.cal) { t = add(t, m.cal); steps.push({ t: `+ ${m.cal} calendar days for ${m.label} = ${fmt(t, false)}`, cite: m.cite }); parts.push(`+ ${m.cal} days ${m.label} (${m.cite}) = ${fmt(t, false)}`); }
    if (m.court) {
      let n = 0, x = t; const sk = [];
      while (n < m.court) { x = add(x, 1); if (courtDay(x, 'ca')) n++; else sk.push(x); }
      steps.push({ t: `+ ${m.court} court days for ${m.label}${sk.length ? ', skipping ' + skipList(sk, 'ca') : ''} = ${fmt(x, false)}`, cite: m.cite });
      parts.push(`+ ${m.court} court days ${m.label} (${m.cite})${sk.length ? ', skipping ' + skipList(sk, 'ca') : ''} = ${fmt(x, false)}`);
      t = x;
    } else {
      const r = rollFwd(t, 'ca', steps, 'CCP §§12, 12a'); if (r.sk.length) parts.push(`${fmt(r.sk[0], false)} is ${HOL.ca.has(r.sk[0]) ? HOL.ca.get(r.sk[0]) : 'a ' + why(r.sk[0], 'ca')}; roll to next court day (CCP §12a) = ${fmt(r.t, false)}`); t = r.t;
    }
  } else {
    let r = rollFwd(t, 'fed', steps, 'FRCP 6(a)(1)(C)'); if (r.sk.length) parts.push(`roll past ${skipList(r.sk, 'fed')} (FRCP 6(a)(1)(C)) = ${fmt(r.t, false)}`); t = r.t;
    if (m.f3) {
      t = add(t, 3); steps.push({ t: `+ 3 days for ${m.label}, added after the period ends = ${fmt(t, false)}`, cite: 'FRCP 6(d)' }); parts.push(`+ 3 days ${m.label} (FRCP 6(d)) = ${fmt(t, false)}`);
      r = rollFwd(t, 'fed', steps, 'FRCP 6(a)(1)(C)'); if (r.sk.length) parts.push(`roll past ${skipList(r.sk, 'fed')} = ${fmt(r.t, false)}`); t = r.t;
    }
  }
  if (m.note) steps.push({ t: m.note, cite: '' });
  const how = mid === 'email' ? 'by email' : mid === 'personal' || mid === 'fpersonal' ? 'by hand' : mid === 'mail' || mid === 'fmail' ? 'by mail' : 'via ' + (m.label || m.en.toLowerCase());
  arith = `Due ${fmt(t)} — served ${how} ` + parts.join('; ') + '.';
  return { due: t, steps, arith };
}

let court = 'ca';
function fillRules() {
  const sel = $('#calRule'), keep = sel.value; sel.innerHTML = '';
  RULES[court].forEach(r => sel.appendChild(el('option', { value: r.id }, TH() ? r.th : r.en)));
  if ([...sel.options].some(o => o.value === keep)) sel.value = keep;
  fillMethods();
}
function fillMethods() {
  const r = RULES[court].find(x => x.id === $('#calRule').value), sel = $('#calMethod'), keep = sel.value; sel.innerHTML = '';
  r.methods.forEach(id => sel.appendChild(el('option', { value: id }, TH() ? METHODS[id].th : METHODS[id].en)));
  if (r.methods.includes(keep)) sel.value = keep; else if (r.methods.includes('email')) sel.value = 'email';
  runCal();
}
let lastCalc = null;
function runCal() {
  const r = RULES[court].find(x => x.id === $('#calRule').value), mid = $('#calMethod').value, v = $('#calServed').value;
  if (!r || !mid || !v) return;
  const res = compute(court, r, mid, parseD(v)); lastCalc = { ...res, rule: r };
  $('#calDue').textContent = fmt(res.due);
  $('#calArith').textContent = res.arith;
  $('#calSteps').innerHTML = res.steps.map(s => `<li>${esc(s.t)}${s.cite ? ` <span class="cite">${esc(s.cite)}</span>` : ''}</li>`).join('');
  drawStatus();
}
document.querySelectorAll('[data-court]').forEach(b => b.addEventListener('click', () => {
  court = b.dataset.court; document.querySelectorAll('[data-court]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); fillRules();
}));
$('#calRule').addEventListener('change', fillMethods);
$('#calMethod').addEventListener('change', runCal);
$('#calServed').addEventListener('input', runCal);

const icsEsc = s => String(s).replace(/\\/g, '\\\\').replace(/;/g, '\\;').replace(/,/g, '\\,').replace(/\n/g, '\\n');
const fold = s => s.match(/.{1,73}/g).join('\r\n ');
$('#calIcs').addEventListener('click', () => {
  if (!lastCalc) return;
  const d = ymd(lastCalc.due).replace(/-/g, ''), nx = ymd(add(lastCalc.due, 1)).replace(/-/g, ''), now = new Date().toISOString().replace(/[-:]/g, '').slice(0, 15) + 'Z';
  const ics = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Cursitor//Demo//EN', 'BEGIN:VEVENT', 'UID:' + Date.now() + '@cursitor', 'DTSTAMP:' + now, 'DTSTART;VALUE=DATE:' + d, 'DTEND;VALUE=DATE:' + nx,
    fold('SUMMARY:' + icsEsc('Due: ' + lastCalc.rule.en + ' — Doe v. Roe (demo)')), fold('DESCRIPTION:' + icsEsc(lastCalc.arith + '\nCheck against the current code, local rules and the court calendar.')), 'END:VEVENT', 'END:VCALENDAR'].join('\r\n');
  const a = el('a', { download: 'deadline.ics' }); a.href = URL.createObjectURL(new Blob([ics + '\r\n'], { type: 'text/calendar' })); document.body.appendChild(a); a.click(); a.remove();
});

/* briefing schedule — CCP §1005(b), counted back */
function backCourt(h, n, c) { let t = h, k = 0; const sk = []; while (k < n) { t = add(t, -1); if (courtDay(t, c)) k++; else sk.push(t); } return { t, sk }; }
function rollBack(t, c) { const sk = []; while (!courtDay(t, c)) { sk.push(t); t = add(t, -1); } return { t, sk }; }
function laInstant(dateStr, timeStr) {
  const [y, m, d] = dateStr.split('-').map(Number), [hh, mm] = (timeStr || '10:00').split(':').map(Number);
  const guess = Date.UTC(y, m - 1, d, hh, mm);
  const p = {}; new Intl.DateTimeFormat('en-US', { timeZone: 'America/Los_Angeles', hourCycle: 'h23', year: 'numeric', month: 'numeric', day: 'numeric', hour: 'numeric', minute: 'numeric' }).formatToParts(guess).forEach(x => p[x.type] = x.value);
  const wall = Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour % 24, +p.minute);
  return guess - (wall - guess);
}
function runHearing() {
  const v = $('#hrDate').value; if (!v) return;
  const h = parseD(v), rows = [];
  const hd = courtDay(h, 'ca') ? '' : ` <span class="badge flag">${why(h, 'ca').toUpperCase()}</span>`;
  const m16 = backCourt(h, 16, 'ca');
  const sk = a => { if (!a.length) return ''; const hol = a.filter(t => HOL.ca.has(t)).reverse().map(t => HOL.ca.get(t)), we = a.filter(t => !HOL.ca.has(t)).length; const bits = []; if (we) bits.push(we + ' weekend days'); if (hol.length) bits.push(hol.join(', ')); return ', skipping ' + bits.join(' and '); };
  rows.push(['Motion — served by hand', m16.t, `${fmt(h, false)} − 16 court days${sk(m16.sk)} (CCP §1005(b))`]);
  const e = backCourt(m16.t, 2, 'ca');
  rows.push(['Motion — served by email', e.t, `16 court days − 2 more court days for e-service${sk(e.sk)} (§1010.6(a)(3)(B))`]);
  const ml = rollBack(add(m16.t, -5), 'ca');
  rows.push(['Motion — served by mail in CA', ml.t, `16 court days − 5 calendar days for mail (§1013(a))${ml.sk.length ? '; ' + fmt(ml.sk[0], false) + ' is not a court day, move earlier' : ''}`]);
  const o = backCourt(h, 9, 'ca');
  rows.push(['Opposition', o.t, `${fmt(h, false)} − 9 court days${sk(o.sk)} (CCP §1005(b))`]);
  const r = backCourt(h, 5, 'ca');
  rows.push(['Reply', r.t, `${fmt(h, false)} − 5 court days${sk(r.sk)} (CCP §1005(b))`]);
  $('#hrRows').innerHTML = rows.map(([a, t, s]) => `<tr><td>${esc(a)}</td><td><b>${fmt(t)}</b></td><td class="cite">${esc(s)}</td></tr>`).join('') +
    `<tr><td colspan="3" class="small muted">${TH() ? 'ศาลรัฐบาลกลางใช้กฎท้องถิ่นของแต่ละเขต สำนักงานใส่ตารางของตนเองได้' : 'Federal briefing schedules come from each district\'s local rules; a firm loads its own table.'}</td></tr>`;
  const inst = laInstant(v, $('#hrTime').value), tz = Intl.DateTimeFormat().resolvedOptions().timeZone || '';
  const mine = new Date(inst).toLocaleString(TH() ? 'th-TH' : 'en-US', { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZoneName: 'short' });
  const la = new Date(inst).toLocaleString(TH() ? 'th-TH' : 'en-US', { timeZone: 'America/Los_Angeles', weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZoneName: 'short' });
  $('#hrTz').innerHTML = (TH() ? `วันพิจารณา: <b>${esc(la)}</b> · เวลาของคุณ (${esc(tz)}): <b>${esc(mine)}</b>` : `Hearing: <b>${esc(la)}</b> · your time (${esc(tz)}): <b>${esc(mine)}</b>`) + hd;
}
$('#hrDate').addEventListener('input', runHearing); $('#hrTime').addEventListener('input', runHearing);

/* scheduled vs proposed */
const ST = [
  { id: 'notice', ev: 'Hearing: Defendant\'s motion to compel, Dec 7, 10:00 a.m.', file: 'Notice of Hearing (filed)', on: false, kind: 'order' },
  { id: 'resp', ev: null, file: 'Proof of service (email, Oct 27)', on: true, kind: 'order' },
  { id: 'moved', ev: 'Responses due, "moved to Dec 15 by agreement"', file: 'Signed stipulation', on: false, kind: 'stip' },
  { id: 'tsc', ev: 'Trial setting conference, January 2027', file: null, on: false, kind: 'order' }
];
function drawStatus() {
  const rows = ST.map(s => {
    const ev = s.id === 'resp' ? `Roe's responses due ${lastCalc ? fmt(lastCalc.due) : ''}` : s.ev;
    let badge;
    if (s.kind === 'stip') badge = s.on ? '<span class="badge sch">SCHEDULED</span>' : '<span class="badge flag">FLAGGED</span>';
    else badge = s.on ? '<span class="badge sch">SCHEDULED</span>' : '<span class="badge pro">PROPOSED</span>';
    const f = s.file ? `<label style="display:flex;gap:8px;align-items:center;cursor:pointer"><input type="checkbox" data-st="${s.id}" ${s.on ? 'checked' : ''} style="width:22px;height:22px"> ${esc(s.file)}</label>` : `<span class="muted">${TH() ? 'ไม่มีคำสั่งในแฟ้ม' : 'No order on file'}</span>`;
    return `<tr><td>${esc(ev)}</td><td>${badge}</td><td>${f}</td></tr>`;
  });
  $('#stRows').innerHTML = rows.join('');
  document.querySelectorAll('[data-st]').forEach(c => c.addEventListener('change', () => { ST.find(s => s.id === c.dataset.st).on = c.checked; drawStatus(); }));
}

/* ======================================================================
   04 LINKS
   ====================================================================== */
const LN_DEFAULT = '/Users/jane/Documents/Doe v. Roe — Alameda (26CV000000)/3 — Discovery [served]/RFP Set One — to Roe Holdings, LLC (final, signed 10-27-26).pdf';
const LN_STOP = new Set('to the of and a an llc inc final signed draft copy v vs'.split(' '));
function runLinks() {
  const p = $('#lnIn').value.trim(); if (!p) return;
  const bad = 'file://' + encodeURI(p).replace(/,/g, '%2C').replace(/\(/g, '%28').replace(/\)/g, '%29');
  $('#lnBad').textContent = bad;
  $('#lnBadN').innerHTML = `<span class="en">Pasted into a browser: ${bad.length} characters</span><span class="th">วางลงเบราว์เซอร์: ${bad.length} ตัวอักษร</span>`;
  const name = p.split('/').pop().replace(/\.[a-z0-9]{1,5}$/i, '').replace(/\([^)]*\)|\[[^\]]*\]/g, ' ');
  const words = name.toLowerCase().normalize('NFKD').replace(/[^\x00-\x7f]/g, '').split(/[^a-z0-9]+/).filter(w => w && !LN_STOP.has(w));
  const home = (p.match(/^\/Users\/[^/]+/) || ['~'])[0];
  const short = home + '/go/' + (words.slice(0, 3).join('-') || 'file');
  $('#lnGood').textContent = short;
}
$('#lnIn').value = LN_DEFAULT; runLinks();
$('#lnIn').addEventListener('input', runLinks);

/* ======================================================================
   05 GATE
   ====================================================================== */
const DRAFT_BAD = `<p>Dear Counsel:</p><p>I write to meet and confer about Roe Holdings' responses to Requests for Production, Set One. <span class="contra">Roe Holdings has produced nothing on the roof.</span> Its responses to Requests Nos. 4 through 6 are evasive, and Plaintiff will move to compel unless complete responses are served by November 20, 2026.</p><p><span class="hit">Ms. Doe would also consider the mediation offer discussed on October 2.</span></p><p>Jane Doe, Plaintiff in Pro Per</p>`;
const DRAFT_OK = `<p>Dear Counsel:</p><p>I write to meet and confer about Roe Holdings' responses to Requests for Production, Set One. Roe Holdings' production on the roof (ROE000114–ROE000131) omits the repair contract and any communication with Bayline Roofing after June 18, 2026. Its responses to Requests Nos. 4 and 6 are evasive, and Plaintiff will move to compel unless complete responses are served by November 20, 2026.</p><p>Jane Doe, Plaintiff in Pro Per</p>`;
const RECS = [
  { f: 'served/RFP-Set-One.pdf', en: 'Request No. 5, served Sep 25', q: 'REQUEST FOR PRODUCTION NO. 5: All DOCUMENTS RELATING TO any inspection or repair of the roof at the PREMISES from January 1, 2025 to the present.' },
  { f: 'received/Roe-Responses-RFP-Set-One.pdf', en: 'Response No. 5, verified Oct 26', q: 'RESPONSE TO REQUEST NO. 5: Responding party will comply and has produced the responsive documents in its possession, Bates ROE000114–ROE000131, including the Bayline Roofing inspection report and invoice dated June 18, 2026.' },
  { f: 'notes/triage.txt', en: 'Triage note, Oct 26', q: 'ROE000114–131 arrived by email Oct 26. Not yet indexed. Bayline invoice says repair "awaiting owner authorization as of June 30."' }
];
let gateFixed = false;
const seen = new Set();
function drawGate() {
  $('#gateLetter').innerHTML = gateFixed ? DRAFT_OK : DRAFT_BAD;
  const unread = RECS.length - seen.size, muzzle = gateFixed ? 0 : 1, contra = !gateFixed && unread === 0;
  const v = $('#gateVerdict'), ok = unread === 0 && muzzle === 0 && gateFixed;
  v.className = 'verdict ' + (ok ? 'cleared' : 'blocked');
  const bits = [];
  if (unread) bits.push(TH() ? `ยังไม่ได้อ่าน ${unread} จาก ${RECS.length} รายการ` : `${unread} of ${RECS.length} records unread`);
  if (muzzle) bits.push(TH() ? 'ติดรายการห้าม 1 จุด: "mediation offer"' : '1 muzzle hit: "mediation offer"');
  if (contra) bits.push(TH() ? 'ร่างขัดกับคำตอบข้อ 5 (ROE000114–131)' : 'draft contradicts Response No. 5 (ROE000114–131)');
  v.textContent = ok ? (TH() ? `ผ่าน — อ่านครบ ${RECS.length} รายการ ไม่ติดรายการห้าม` : `CLEARED — read ${RECS.length} of ${RECS.length} records; no muzzle hits`) : (TH() ? 'ล็อก — ' : 'BLOCKED — ') + bits.join(' · ');
  $('#gateSend').disabled = !ok;
}
$('#gateRecs').innerHTML = RECS.map((r, i) => `<details class="rec" data-i="${i}"><summary>${esc(r.f)} <span class="muted small">· ${esc(r.en)}</span><span class="seen"><span class="en">✓ read</span><span class="th">✓ อ่านแล้ว</span></span></summary><blockquote>${esc(r.q)}</blockquote></details>`).join('');
document.querySelectorAll('details.rec').forEach(d => d.addEventListener('toggle', () => { if (d.open) { seen.add(d.dataset.i); drawGate(); } }));
$('#gateFix').addEventListener('click', () => { gateFixed = !gateFixed; drawGate(); });
$('#gateSend').addEventListener('click', () => { $('#gateVerdict').textContent = TH() ? 'เข้ากล่องรอส่งแล้ว รอคนลงนามและส่ง' : 'In the outbox, waiting for a person to sign and serve.'; $('#gateSend').disabled = true; });

/* ======================================================================
   06 BRIEF + FORK — built from today's date with the same calendar engine
   ====================================================================== */
function today() { const n = new Date(); return D(n.getFullYear(), n.getMonth() + 1, n.getDate()); }
function nextCourt(t, n) { let k = 0; while (k < n) { t = add(t, 1); if (courtDay(t, 'ca')) k++; } return t; }
let briefData = null;
function renderBrief() {
  const t0 = today();
  const hearing = nextCourt(t0, 12), opp = backCourt(hearing, 9, 'ca').t, reply = backCourt(hearing, 5, 'ca').t;
  const served = add(t0, -24), resp = compute('ca', RULES.ca[0], 'email', served);
  briefData = { opp };
  const pad = s => (s + '            ').slice(0, 14);
  const L = [];
  L.push('CURSITOR · MORNING BRIEF', 'Doe v. Roe Holdings, LLC (fictional)', fmt(t0), '');
  L.push('DUE TODAY');
  L.push('  ' + pad(fmt(t0, false)) + 'Meet-and-confer letter out (target; gate: BLOCKED)', '');
  L.push('NEXT 7 DAYS');
  const wk = [[opp, 'Opposition to motion to compel (CCP §1005(b): 9 court days before ' + fmt(hearing, false) + ')'], [reply, 'Their reply (5 court days before hearing)']].filter(([d]) => d - t0 <= 7 * DAY && d >= t0);
  if (wk.length) wk.forEach(([d, s]) => L.push('  ' + pad(fmt(d, false)) + s)); else L.push('  —');
  L.push('', 'CLOCKS RUNNING');
  L.push('  Roe\'s responses to Special Interrogatories, Set One', '  ' + resp.arith, '');
  L.push('PROPOSED — NO ORDER ON FILE', '  Trial setting conference, January 2027', '');
  L.push('FLAGGED', '  Responses "moved to Dec 15" — no signed stipulation on file', '');
  L.push('DOCKET (CourtListener RECAP)', '  No new entries since yesterday.', '');
  L.push('OPEN FORKS', '  Oppose the motion to compel, or comply? Expires ' + fmt(opp, false) + '.');
  $('#briefOut').textContent = L.join('\n');
  $('#forkExp').textContent = fmt(opp) + (TH() ? ' (วันยื่นคำคัดค้าน)' : ' (opposition due)');
  if (lastCalc) drawStatus();
  if ($('#calRule').options.length) { fillRules(); runHearing(); drawGate(); }
}
document.querySelectorAll('#forkOpts .opt').forEach(b => b.addEventListener('click', () => {
  document.querySelectorAll('#forkOpts .opt').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
  const ch = b.querySelector('b').textContent, ts = new Date().toISOString().slice(0, 16).replace('T', ' ');
  $('#forkLog').textContent = TH() ? `เลือก ${ch} · โดยคุณ · ${ts} — บันทึกต่อท้าย decisions.jsonl` : `Chose ${ch} · by you · ${ts} — appended to decisions.jsonl`;
}));

/* boot */
let initial = store.get('cursitor-lang');
if (!initial) initial = (navigator.language || '').toLowerCase().startsWith('th') ? 'th' : 'en';
fillRules(); runHearing(); drawGate();
setLang(initial);
})();
