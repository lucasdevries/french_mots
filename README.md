# Mots — NL → FR flashcards

Quiz yourself on French words and short phrases, per lesson, with flashcards.
Same setup as the `learn_french` (Shadow YouTube) project: Python stdlib only,
one self-contained static site, progress stored in the browser.

**Live (deployed) app:** https://mots-nl-fr.netlify.app

## How it works

```
lists/*.csv ─▶ build_static.py ─▶ site/ ─▶ Netlify (static, no backend)
 (nl,fr)        (bundles all)      (PWA)
```

No dependencies, no server: `build_static.py` reads the CSVs and generates a
self-contained `site/` folder (app + `lessons.json` + PWA manifest + service
worker). All progress lives per-device in the browser (localStorage).

## Features

- **Lessons** — pick a lesson; the list and progress bar show how many cards
  you've learned per lesson.
- **Flashcards** — you see the Dutch → **Show** → the French translation →
  **✓ Correct** / **✗ Wrong**. Random order; wrong cards come back once at
  the end (retry round). Correct once = learned.
- **Start new / Start all** — only the not-yet-learned cards, or the whole
  lesson.
- **Test (25)** — 25 random cards from all lessons that are at 80%+.
  You get a score; doesn't count towards progress (and no retry round).
- **Tricky (n)** — practice session with the cards you got wrong most often
  (wrong = +1, correct = −1; max 20 per session, most-wrong first).
- **⌨️ Type** (toggle) — type the French translation yourself; enter = check.
  Accent-only mistakes still count as correct ("almost"), and on a wrong
  answer you can still pick **Count it correct** (e.g. for a typo).
- **🔊 Pronounce** — speaks the French answer via browser TTS. Also works on
  iPhone (mind the mute switch; you can download a better voice via
  Settings → Accessibility → Spoken Content).
- **Reset lesson** — clears the progress of the selected lesson only.
- Shortcuts: `space` = show · `→` = correct · `←` = wrong · `enter` = check/next.
- Light/dark theme, installable as a PWA (*Add to Home Screen*), works offline.

## Adding or editing a lesson

Drop a CSV in `lists/` (header `nl,fr`, one card per line):

```csv
nl,fr
"graag frieten eten","aimer les frites"
```

The filename (without `.csv`) becomes the lesson name, e.g. `1.1.csv` → lesson 1.1.
Then:

```bash
./deploy.sh     # rebuilds site/ and pushes it live
```

## Testing locally (free, no deploy)

```bash
./run.sh        # builds site/ and opens http://localhost:8002
```

## Deploying

```bash
./deploy.sh     # python3 build_static.py + netlify deploy --dir site --prod
```

The folder is already linked to the Netlify project `mots-nl-fr` (see
`.netlify/state.json`), so deploying is a single command. Progress ("learned")
lives per-device in the browser and survives deploys.

## Layout

```
build_static.py    bundles lists/*.csv into a static PWA in site/
run.sh             build locally + preview on :8002
deploy.sh          build + netlify deploy --prod
lists/<lesson>.csv the words/phrases (nl,fr)
site/              generated static site              [gitignored]
```

## Later / ideas

- Spaced repetition (Leitner boxes) instead of "correct once = learned".
- Reverse direction (FR → NL).
- Test history (scores over time).
