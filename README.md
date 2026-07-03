# Mots — NL → FR flashcards

Overhoor jezelf op Franse woordjes en korte zinnetjes, per les, met flashcards.
Zelfde opzet als het `learn_french` (Shadow YouTube) project: Python stdlib
only, één zelfstandige statische site, progress in de browser.

**Live (deployed) app:** https://mots-nl-fr.netlify.app

## Hoe het werkt

```
lists/*.csv ─▶ build_static.py ─▶ site/ ─▶ Netlify (statisch, geen backend)
 (nl,fr)        (bundelt alles)    (PWA)
```

Geen dependencies, geen server: `build_static.py` leest de CSV's en genereert
een self-contained `site/` map (app + `lessons.json` + PWA manifest + service
worker). Alle voortgang staat per apparaat in de browser (localStorage).

## Features

- **Lessen** — kies een les; de lijst en voortgangsbalk tonen per les hoeveel
  kaarten je geleerd hebt.
- **Overhoren** — je ziet het Nederlands → **Toon** → de Franse vertaling →
  **✓ Goed** / **✗ Fout**. Random volgorde; foute kaarten krijg je aan het
  eind nog één keer (foute ronde). Eén keer goed = geleerd.
- **Start nieuwe / Start alles** — alleen nog-niet-geleerde kaarten, of de
  hele les.
- **Toets (25)** — 25 willekeurige kaarten uit alle lessen die op 80%+ staan.
  Je krijgt een score; telt niet mee voor de progress (en geen foute ronde).
- **Lastig (n)** — oefensessie met de kaarten die je het vaakst fout had
  (fout = +1, goed = −1; max 20 per sessie, vaakst-fout eerst).
- **⌨️ Typen** (toggle) — typ zelf de Franse vertaling; enter = check. Alleen
  accentfouten tellen nog als goed ("bijna"), en bij fout kun je alsnog
  **Toch goed** kiezen (bijv. bij een tikfout).
- **🔊 Uitspraak** — spreekt het Franse antwoord uit via browser-TTS. Werkt
  ook op iPhone (let op het mute-schuifje; betere stem downloaden kan via
  Instellingen → Toegankelijkheid → Gesproken materiaal).
- **Reset les** — wist de progress van alleen de geselecteerde les.
- Sneltoetsen: `spatie` = toon · `→` = goed · `←` = fout · `enter` = check/volgende.
- Licht/donker thema, installeerbaar als PWA (*Add to Home Screen*), werkt offline.

## Les toevoegen of aanpassen

Zet een CSV in `lists/` (header `nl,fr`, één kaart per regel):

```csv
nl,fr
"graag frieten eten","aimer les frites"
```

De bestandsnaam (zonder `.csv`) wordt de lesnaam, bijv. `1.1.csv` → les 1.1.
Daarna:

```bash
./deploy.sh     # bouwt site/ opnieuw en zet hem live
```

## Lokaal testen (gratis, geen deploy)

```bash
./run.sh        # bouwt site/ en opent http://localhost:8002
```

## Deployen

```bash
./deploy.sh     # python3 build_static.py + netlify deploy --dir site --prod
```

De map is al gekoppeld aan het Netlify-project `mots-nl-fr` (zie
`.netlify/state.json`), dus deployen is één commando. Progress ("geleerd")
staat per apparaat in de browser en overleeft deploys gewoon.

## Layout

```
build_static.py    bundelt lists/*.csv naar een statische PWA in site/
run.sh             lokaal bouwen + preview op :8002
deploy.sh          bouwen + netlify deploy --prod
lists/<les>.csv    de woordjes/zinnetjes (nl,fr)
site/              gegenereerde statische site        [gitignored]
```

## Later / ideeën

- Gespreide herhaling (Leitner-boxen) i.p.v. "ooit goed = geleerd".
- Richting omdraaien (FR → NL).
- Toets-geschiedenis (scores over tijd).
