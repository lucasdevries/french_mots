#!/usr/bin/env python3
"""
Build a static version of Mots (NL -> FR flashcards) that needs no server.

    python3 build_static.py

Reads every CSV in `lists/` (format: header `nl,fr`, one card per line) and
creates a self-contained `site/` folder:
  site/
    index.html        the app (no backend; reads lessons.json)
    lessons.json      all lessons (cards with ids)
    manifest.json     PWA manifest (installable on phone)
    sw.js             service worker (offline caching)
    icon-192.png      icons (solid colour)
    icon-512.png

Deploy it anywhere that serves static files over HTTPS:
  - Netlify:  ./deploy.sh   (or drag `site/` onto https://app.netlify.com/drop)
  - Preview locally:  ./run.sh  -> http://localhost:8002

Progress ("geleerd") is stored per-device in the browser. Re-run this after
adding/changing a CSV in lists/, then re-deploy.

Same approach as the learn_french project: Python stdlib only, everything
inlined into one index.html.
"""

import os
import re
import csv
import json
import time
import zlib
import struct
import shutil
import hashlib

BASE       = os.path.dirname(os.path.abspath(__file__))
LISTS_DIR  = os.path.join(BASE, "lists")
SITE_DIR   = os.path.join(BASE, "site")
ACCENT     = (255, 159, 67)  # icon colour (orange, so it differs from Shadow's blue)


def card_id(nl, fr):
    return hashlib.md5(f"{nl}|{fr}".encode("utf-8")).hexdigest()[:12]


def natural_key(s):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]


# ---------------------------------------------------------------------------
# Collect lessons from lists/*.csv -> lessons.json
# ---------------------------------------------------------------------------
def collect_lessons():
    lessons = []
    for fname in sorted(os.listdir(LISTS_DIR), key=natural_key):
        if not fname.lower().endswith(".csv"):
            continue
        path = os.path.join(LISTS_DIR, fname)
        cards = []
        with open(path, encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 2:
                    continue
                nl, fr = row[0].strip(), row[1].strip()
                if not nl or not fr or (nl.lower(), fr.lower()) == ("nl", "fr"):
                    continue  # skip header + empty lines
                cards.append({"id": card_id(nl, fr), "nl": nl, "fr": fr})
        if cards:
            slug = os.path.splitext(fname)[0]
            lessons.append({
                "slug": slug,
                "title": slug,
                "total": len(cards),
                "cards": cards,
            })
    return lessons


# ---------------------------------------------------------------------------
# Minimal solid-colour PNG (no Pillow needed) for the PWA icons
# ---------------------------------------------------------------------------
def solid_png(size, rgb):
    row = b"\x00" + bytes(rgb) * size
    raw = row * size
    comp = zlib.compress(raw, 9)

    def chunk(typ, data):
        return (struct.pack(">I", len(data)) + typ + data +
                struct.pack(">I", zlib.crc32(typ + data) & 0xffffffff))

    sig  = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)  # 8-bit RGB
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", comp) + chunk(b"IEND", b"")


MANIFEST = {
    "name": "Mots — NL naar FR",
    "short_name": "Mots",
    "start_url": ".",
    "scope": ".",
    "display": "standalone",
    "background_color": "#f3f3f3",
    "theme_color": "#f3f3f3",
    "icons": [
        {"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
        {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"},
    ],
}

SERVICE_WORKER = """\
// Versioned caching. The app shell + lessons.json use network-first (always
// fresh when online, cached copy as offline fallback); icons use cache-first.
// CACHE is stamped on every build and old caches are deleted on activate, so
// deploys propagate to installed PWAs.
const CACHE = 'mots-__VERSION__';

self.addEventListener('install', e => self.skipWaiting());

self.addEventListener('activate', e => e.waitUntil(
  caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim())
));

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  const fresh = e.request.mode === 'navigate' || url.pathname.endsWith('/lessons.json');
  if (fresh) {
    e.respondWith(
      fetch(e.request).then(resp => {
        const copy = resp.clone();
        caches.open(CACHE).then(c => c.put(e.request, copy));
        return resp;
      }).catch(() => caches.match(e.request))
    );
  } else {
    e.respondWith(
      caches.match(e.request).then(hit => hit || fetch(e.request).then(resp => {
        if (resp.ok) { const copy = resp.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); }
        return resp;
      }))
    );
  }
});
"""

INDEX_HTML = r"""<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<link rel="manifest" href="manifest.json">
<link rel="apple-touch-icon" href="icon-192.png">
<title>Mots — NL → FR</title>
<style>
  :root { --bg:#f3f3f3; --card:#ffffff; --line:#e4e4e8; --txt:#1a1c22;
          --muted:#6b7280; --accent:#4f9cff; --done:#2ec16b; --bad:#e05a5a; --btn:#f0f0f3; }
  :root[data-theme="dark"] {
          --bg:#0f1115; --card:#171a21; --line:#262b36; --txt:#e6e9ef;
          --muted:#8b93a7; --accent:#4f9cff; --done:#2ec16b; --bad:#e05a5a; --btn:#222734; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--txt);
         font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
  .wrap { max-width:560px; margin:0 auto; padding:24px 16px 64px; }
  h1 { font-size:20px; margin:0 0 16px; display:flex; align-items:center; gap:8px; }
  .row-top { display:flex; align-items:center; gap:10px; margin-bottom:14px; flex-wrap:wrap; }
  .row-top.tight { margin-bottom:8px; }
  select { padding:9px 34px 9px 12px; border-radius:10px; border:1px solid var(--line);
           background:var(--card); color:var(--txt); font-size:15px; flex:1; min-width:160px;
           -webkit-appearance:none; appearance:none;
           background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='%238b93a7' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'><path d='M6 9l6 6 6-6'/></svg>");
           background-repeat:no-repeat; background-position:right 12px center; }
  .count { color:var(--muted); font-size:14px; white-space:nowrap; }
  .pill { padding:9px 12px; border-radius:10px; border:1px solid var(--line);
          background:var(--card); color:var(--txt); font-size:14px; cursor:pointer;
          white-space:nowrap; }
  .pill:hover { border-color:var(--accent); }
  .pill.active { border-color:var(--accent); color:var(--accent); }
  .pill:disabled { opacity:.45; cursor:default; }
  .pill:disabled:hover { border-color:var(--line); }
  .pill.danger:hover { border-color:var(--bad); color:var(--bad); }
  #typeInput { flex:1; padding:12px 14px; border-radius:12px; border:1px solid var(--line);
               background:var(--card); color:var(--txt); font-size:16px; min-width:0; }
  #typeInput:focus { outline:none; border-color:var(--accent); }
  #typeFb { font-size:15px; }
  .bar { height:8px; border-radius:4px; background:var(--btn); border:1px solid var(--line);
         overflow:hidden; margin:6px 0 16px; }
  .bar > div { height:100%; background:var(--done); width:0; transition:width .2s; }
  .fcard { background:var(--card); border:1px solid var(--line); border-radius:12px;
           padding:34px 22px; text-align:center; margin-bottom:14px; min-height:220px;
           display:flex; flex-direction:column; justify-content:center; gap:14px; }
  .nl { font-size:22px; }
  .fr { font-size:22px; color:var(--accent); border-top:1px solid var(--line); padding-top:14px; }
  .actions { display:flex; gap:10px; justify-content:center; }
  .btn { padding:12px 22px; border-radius:12px; border:1px solid var(--line);
         background:var(--btn); color:var(--txt); font-size:16px; cursor:pointer; }
  .btn:hover { border-color:var(--accent); }
  .btn.good { border-color:var(--done); color:var(--done); }
  .btn.bad  { border-color:var(--bad);  color:var(--bad); }
  .btn.good:hover { background:var(--done); color:#fff; }
  .btn.bad:hover  { background:var(--bad);  color:#fff; }
  .banner { text-align:center; color:var(--bad); font-size:14px; margin-bottom:8px; }
  .hint { color:var(--muted); font-size:13px; text-align:center; }
  .theme-toggle { position:fixed; top:14px; right:14px; width:34px; height:34px;
          border-radius:50%; border:1px solid var(--line); background:var(--card);
          color:var(--txt); font-size:15px; cursor:pointer; line-height:1; z-index:10; }
  .empty { color:var(--muted); text-align:center; padding:40px; }
  .summary { text-align:center; font-size:18px; margin:8px 0 4px; }
  .hidden { display:none !important; }
</style>
</head>
<body>
<button class="theme-toggle" id="themeToggle" title="Toggle light/dark">🌙</button>
<div class="wrap">
  <h1>🇫🇷 Mots — NL → FR</h1>

  <!-- lesson picker -->
  <div id="pick">
    <div class="row-top tight">
      <select id="lessonSelect"></select>
    </div>
    <div class="count" id="pickCount"></div>
    <div class="bar"><div id="pickBar"></div></div>
    <div class="row-top">
      <button class="pill" id="startNew"></button>
      <button class="pill" id="startAll"></button>
      <button class="pill danger" id="resetLesson" style="margin-left:auto">Reset les</button>
    </div>
    <div class="row-top">
      <button class="pill" id="testBtn">Toets (25)</button>
      <button class="pill" id="weakBtn">Lastig</button>
      <button class="pill" id="typeToggle" title="Antwoord zelf typen">⌨️ Typen</button>
    </div>
    <div class="count" id="testHint"></div>
  </div>

  <!-- flashcard session -->
  <div id="session" class="hidden">
    <div class="row-top">
      <button class="pill" id="stopBtn">← Stop</button>
      <span class="count" id="sessCount" style="margin-left:auto"></span>
    </div>
    <div class="banner hidden" id="retryBanner">Foute ronde — nog een keer</div>
    <div class="banner hidden" id="testBanner" style="color:var(--accent)">Toets — telt niet mee voor progress</div>
    <div class="fcard">
      <div class="nl" id="cardNl"></div>
      <div class="fr hidden" id="cardFr"></div>
      <div class="hidden" id="typeFb"></div>
      <div class="actions hidden" id="speakRow">
        <button class="pill" id="speakBtn" title="Spreek uit">🔊</button>
      </div>
    </div>
    <div class="actions" id="showActions">
      <button class="btn" id="showBtn">Toon</button>
    </div>
    <div class="actions hidden" id="typeActions">
      <input id="typeInput" autocomplete="off" autocapitalize="off" autocorrect="off"
             spellcheck="false" placeholder="Typ de Franse vertaling…">
      <button class="btn" id="checkBtn">Check</button>
    </div>
    <div class="actions hidden" id="judgeActions">
      <button class="btn bad" id="badBtn">✗ Fout</button>
      <button class="btn good" id="goodBtn">✓ Goed</button>
    </div>
    <div class="actions hidden" id="nextActions">
      <button class="btn good" id="nextBtn">Volgende →</button>
    </div>
    <p class="hint" id="kbHint"></p>
  </div>

  <!-- session done -->
  <div id="done" class="hidden">
    <div class="fcard">
      <div class="summary" id="doneSummary"></div>
      <div class="count" id="doneDetail"></div>
    </div>
    <div class="actions">
      <button class="btn" id="againBtn">Opnieuw</button>
      <button class="btn" id="backBtn">Terug naar lessen</button>
    </div>
  </div>
</div>
<script>
const $ = s => document.querySelector(s);
let lessons = [], current = 0;

// Progress ("geleerd") is stored per-device in the browser: {slug: [id, ...]}.
let learned = JSON.parse(localStorage.getItem('learned') || '{}');
function saveLearned() { localStorage.setItem('learned', JSON.stringify(learned)); }
function learnedSet(slug) { return new Set(learned[slug] || []); }
function markLearned(slug, id) {
  const set = learnedSet(slug);
  if (set.has(id)) return;
  set.add(id); learned[slug] = [...set]; saveLearned();
}

// Per-card mistake counter across all lessons: fout -> +1, goed -> -1 (min 0).
// Cards with a positive count feed the "Lastig" session.
let wrong = JSON.parse(localStorage.getItem('wrong') || '{}');
function bumpWrong(id, d) {
  const n = (wrong[id] || 0) + d;
  if (n <= 0) delete wrong[id]; else wrong[id] = n;
  localStorage.setItem('wrong', JSON.stringify(wrong));
}
function weakPool() {
  const cards = [];
  lessons.forEach(l => l.cards.forEach(c => {
    if (wrong[c.id]) cards.push({ ...c, slug: l.slug, n: wrong[c.id] });
  }));
  return cards.sort((a, b) => b.n - a.n);  // vaakst fout eerst
}

// Theme
function applyTheme(t) {
  document.documentElement.setAttribute('data-theme', t);
  $('#themeToggle').textContent = t === 'dark' ? '☀️' : '🌙';
}
applyTheme(localStorage.getItem('theme') || 'light');
$('#themeToggle').onclick = () => {
  const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  localStorage.setItem('theme', next); applyTheme(next);
};

// Type mode (answer by typing) — optional toggle, persisted.
let typeOn = localStorage.getItem('typemode') === '1';
function updateTypeBtn() { $('#typeToggle').classList.toggle('active', typeOn); }
$('#typeToggle').onclick = () => {
  typeOn = !typeOn; localStorage.setItem('typemode', typeOn ? '1' : '0'); updateTypeBtn();
};
updateTypeBtn();

// French TTS via the browser's speechSynthesis (works on iPhone too;
// needs a tap to start — the 🔊 button — and the mute switch silences it).
let frVoice = null;
const hasTTS = 'speechSynthesis' in window;
function pickVoice() {
  const vs = speechSynthesis.getVoices();
  frVoice = vs.find(v => v.lang === 'fr-FR') || vs.find(v => v.lang.startsWith('fr')) || null;
}
if (hasTTS) { pickVoice(); speechSynthesis.onvoiceschanged = pickVoice; }
function speak(text) {
  if (!hasTTS) return;
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = 'fr-FR'; if (frVoice) u.voice = frVoice; u.rate = 0.9;
  speechSynthesis.speak(u);
}
$('#speakBtn').onclick = () => { if (card) speak(card.fr); };

// Lenient answer comparison for type mode.
function norm(s) {
  return s.toLowerCase().normalize('NFC').replace(/[’‘]/g, "'")
          .replace(/\s+/g, ' ').replace(/[.!?\u2026\u00a0 ]+$/g, '').trim();
}
function deacc(s) { return s.normalize('NFD').replace(/[\u0300-\u036f]/g, ''); }

function shuffle(a) {
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// ---- lesson picker -------------------------------------------------------
function show(id) {
  ['pick', 'session', 'done'].forEach(s => $('#' + s).classList.toggle('hidden', s !== id));
}

function renderPick() {
  const sel = $('#lessonSelect'); sel.innerHTML = '';
  lessons.forEach((l, i) => {
    const d = l.cards.filter(c => learnedSet(l.slug).has(c.id)).length;
    const o = document.createElement('option');
    o.value = i; o.textContent = `Les ${l.title} — ${d}/${l.total} geleerd`;
    sel.appendChild(o);
  });
  sel.value = current;
  const l = lessons[current];
  if (!l) { $('#pickCount').textContent = 'Geen lessen.'; return; }
  const set = learnedSet(l.slug);
  const d = l.cards.filter(c => set.has(c.id)).length;
  const fresh = l.total - d;
  $('#pickCount').textContent = `${d} / ${l.total} geleerd`;
  $('#pickBar').style.width = (l.total ? (100 * d / l.total) : 0) + '%';
  $('#startNew').textContent = `Start nieuwe (${fresh})`;
  $('#startNew').disabled = fresh === 0;
  $('#startAll').textContent = `Start alles (${l.total})`;
  const pool = testPool();
  $('#testBtn').disabled = pool.cards.length === 0;
  $('#testHint').textContent = pool.lessons.length
    ? `uit ${pool.lessons.length} les${pool.lessons.length === 1 ? '' : 'sen'} op 80%+ (${pool.lessons.join(', ')})`
    : 'nog geen les op 80%+';
  const weak = weakPool();
  $('#weakBtn').textContent = `Lastig (${Math.min(weak.length, 20)})`;
  $('#weakBtn').disabled = weak.length === 0;
  show('pick');
}

// Lessons at >=80% learned supply the test pool.
function testPool() {
  const cards = [], names = [];
  lessons.forEach(l => {
    const set = learnedSet(l.slug);
    const d = l.cards.filter(c => set.has(c.id)).length;
    if (l.total && d / l.total >= 0.8) {
      names.push(l.title);
      cards.push(...l.cards);
    }
  });
  return { cards, lessons: names };
}

$('#lessonSelect').onchange = e => { current = +e.target.value; renderPick(); };

$('#resetLesson').onclick = () => {
  const l = lessons[current];
  if (!l) return;
  if (!confirm(`Progress van les ${l.title} wissen?`)) return;
  delete learned[l.slug]; saveLearned(); renderPick();
};

// ---- flashcard session ---------------------------------------------------
let queue = [], retryQueue = [], card = null, revealed = false;
let inRetry = false, isTest = false, roundTotal = 0, roundDone = 0, nGood = 0, nBad = 0, lastMode = 'new';

function startSession(mode) {
  isTest = mode === 'test';
  let cards;
  if (isTest) {
    cards = shuffle(testPool().cards.slice()).slice(0, 25);
  } else if (mode === 'weak') {
    cards = weakPool().slice(0, 20);       // vaakst-fout eerst, max 20 per sessie
  } else {
    const l = lessons[current];
    if (!l) return;
    const set = learnedSet(l.slug);
    cards = mode === 'new' ? l.cards.filter(c => !set.has(c.id)) : l.cards.slice();
  }
  if (!cards.length) return;
  lastMode = mode;
  queue = shuffle(cards.slice());
  retryQueue = [];
  inRetry = false; roundTotal = queue.length; roundDone = 0; nGood = 0; nBad = 0;
  $('#retryBanner').classList.add('hidden');
  $('#testBanner').classList.toggle('hidden', !isTest);
  show('session');
  nextCard();
}
$('#startNew').onclick = () => startSession('new');
$('#startAll').onclick = () => startSession('all');
$('#testBtn').onclick = () => startSession('test');
$('#weakBtn').onclick = () => startSession('weak');
$('#stopBtn').onclick = () => renderPick();

function nextCard() {
  if (!queue.length) {
    if (!isTest && !inRetry && retryQueue.length) {   // foute ronde aan het eind
      inRetry = true;
      queue = shuffle(retryQueue.slice()); retryQueue = [];
      roundTotal = queue.length; roundDone = 0;
      $('#retryBanner').classList.remove('hidden');
    } else {
      return endSession();
    }
  }
  card = queue.shift(); revealed = false; roundDone++;
  $('#sessCount').textContent = `${roundDone} / ${roundTotal}`;
  $('#cardNl').textContent = card.nl;
  $('#cardFr').textContent = card.fr;
  $('#cardFr').classList.add('hidden');
  $('#typeFb').classList.add('hidden');
  $('#speakRow').classList.add('hidden');
  $('#judgeActions').classList.add('hidden');
  $('#nextActions').classList.add('hidden');
  $('#goodBtn').textContent = '✓ Goed';
  $('#showActions').classList.toggle('hidden', typeOn);
  $('#typeActions').classList.toggle('hidden', !typeOn);
  if (typeOn) { const inp = $('#typeInput'); inp.value = ''; inp.focus(); }
  $('#kbHint').textContent = typeOn ? 'enter = check' : 'spatie = toon · ← = fout · → = goed';
}

function showAnswer() {
  $('#cardFr').classList.remove('hidden');
  if (hasTTS) $('#speakRow').classList.remove('hidden');
}

function reveal() {
  if (revealed) return;
  revealed = true;
  showAnswer();
  $('#showActions').classList.add('hidden');
  $('#judgeActions').classList.remove('hidden');
}
$('#showBtn').onclick = reveal;

// Type mode: compare the typed answer; only accent mistakes still count as good.
function check() {
  if (revealed) return;
  revealed = true;
  const guess = $('#typeInput').value;
  showAnswer();
  $('#typeActions').classList.add('hidden');
  const fb = $('#typeFb');
  fb.classList.remove('hidden');
  if (norm(guess) && norm(guess) === norm(card.fr)) {
    fb.textContent = '✓ Goed!'; fb.style.color = 'var(--done)';
    $('#nextActions').classList.remove('hidden');
  } else if (norm(guess) && deacc(norm(guess)) === deacc(norm(card.fr))) {
    fb.textContent = '≈ Bijna — let op de accenten'; fb.style.color = 'var(--done)';
    $('#nextActions').classList.remove('hidden');
  } else {
    fb.textContent = norm(guess) ? `Jij typte: ${guess}` : 'Geen antwoord';
    fb.style.color = 'var(--bad)';
    $('#goodBtn').textContent = '✓ Toch goed';
    $('#judgeActions').classList.remove('hidden');
  }
}
$('#checkBtn').onclick = check;
$('#nextBtn').onclick = () => judge(true);

function judge(good) {
  if (!revealed) return;
  bumpWrong(card.id, good ? -1 : 1);
  if (good) {
    nGood++;
    if (!isTest) markLearned(card.slug || lessons[current].slug, card.id);  // toets telt niet mee
  } else {
    nBad++;
    if (!isTest && !inRetry) retryQueue.push(card);
  }
  nextCard();
}
$('#goodBtn').onclick = () => judge(true);
$('#badBtn').onclick = () => judge(false);

function endSession() {
  if (isTest) {
    const pct = Math.round(100 * nGood / roundTotal);
    $('#doneSummary').textContent = `${pct >= 80 ? '🎉 ' : ''}Toets: ${nGood} / ${roundTotal} goed — ${pct}%`;
    $('#doneDetail').textContent = 'telt niet mee voor progress';
  } else if (lastMode === 'weak') {
    const left = weakPool().length;
    $('#doneSummary').textContent = nBad === 0 ? '🎉 Alles goed!' : `Klaar — ${nGood} goed, ${nBad} fout`;
    $('#doneDetail').textContent = left ? `nog ${left} lastige kaarten` : 'geen lastige kaarten meer 💪';
  } else {
    const l = lessons[current];
    const d = l.cards.filter(c => learnedSet(l.slug).has(c.id)).length;
    $('#doneSummary').textContent = nBad === 0 ? '🎉 Alles goed!' : `Klaar — ${nGood} goed, ${nBad} fout`;
    $('#doneDetail').textContent = `Les ${l.title}: ${d} / ${l.total} geleerd`;
  }
  show('done');
}
$('#againBtn').onclick = () => startSession(lastMode);
$('#backBtn').onclick = () => renderPick();

document.addEventListener('keydown', e => {
  if ($('#session').classList.contains('hidden')) return;
  if (e.target === $('#typeInput')) {            // typen: alleen enter afvangen
    if (e.key === 'Enter') { e.preventDefault(); check(); }
    return;
  }
  if (e.key === 'Enter' && !$('#nextActions').classList.contains('hidden')) { judge(true); return; }
  if (e.key === ' ') { e.preventDefault(); if (!typeOn) reveal(); }
  else if (e.key === 'ArrowRight') judge(true);
  else if (e.key === 'ArrowLeft') judge(false);
});

async function load() {
  lessons = await (await fetch('lessons.json')).json();
  current = 0;
  if (!lessons.length) { $('#pickCount').textContent = 'Geen lessen.'; return; }
  renderPick();
}
load();

if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js', { updateViaCache: 'none' }).catch(() => {});
</script>
</body>
</html>"""


def main():
    if not os.path.isdir(LISTS_DIR):
        print("No lists/ directory — add a CSV first.")
        return
    lessons = collect_lessons()
    if not lessons:
        print("No lessons found in lists/*.csv.")
        return

    if os.path.exists(SITE_DIR):
        shutil.rmtree(SITE_DIR)
    os.makedirs(SITE_DIR, exist_ok=True)

    with open(os.path.join(SITE_DIR, "lessons.json"), "w", encoding="utf-8") as f:
        json.dump(lessons, f, ensure_ascii=False)
    with open(os.path.join(SITE_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(INDEX_HTML)
    with open(os.path.join(SITE_DIR, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(MANIFEST, f)
    with open(os.path.join(SITE_DIR, "sw.js"), "w", encoding="utf-8") as f:
        f.write(SERVICE_WORKER.replace("__VERSION__", str(int(time.time()))))
    with open(os.path.join(SITE_DIR, "icon-192.png"), "wb") as f:
        f.write(solid_png(192, ACCENT))
    with open(os.path.join(SITE_DIR, "icon-512.png"), "wb") as f:
        f.write(solid_png(512, ACCENT))

    cards = sum(l["total"] for l in lessons)
    print(f"Built site/ — {len(lessons)} lessen, {cards} kaarten.")
    for l in lessons:
        print(f"  {l['title']}: {l['total']} kaarten")
    print("Preview: ./run.sh -> http://localhost:8002")
    print("Deploy:  ./deploy.sh")


if __name__ == "__main__":
    main()
