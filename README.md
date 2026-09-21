# nobodybeatstheviz.com

The personal site of George "Wax" Weatherwax — NBTV, The Viz, P3 stage.

Static HTML/CSS, deployed via GitHub Pages from `main`.

- **Homepage:** [`index.html`](index.html) — hero → the game notes → the lineup (nine innings, in order) → the away games → who keeps score → footer. The shape and the copy rulings live in the wax-system repo (`nbtv-brand/website-positioning.md`, `the-viz-persona.md`).
- **Bits:** [`bits/`](bits/) — one folder per piece. `bits/wax-baseball/` is the game notes (inning zero).
- **Logo + brand assets** live in the parent Wax-System Drive folder, not in this repo.

## Build

The site has one generated span. Everything else is hand-authored HTML.

- **Source:** [`bits/pieces.json`](bits/pieces.json) — one row per piece (innings, away games, the notes): label, question, working title, tools, status, url, date.
- **Generator:** [`build_bits.py`](build_bits.py) — renders the lineup and away-games card grids into `index.html` between `<!-- INNINGS:START/END -->` and `<!-- AWAY:START/END -->`. Stdlib only, idempotent.
- **When to run:** after any edit to `pieces.json` — an inning lands (set `url`, `date`, `status: on-wax`), a question is reworded, a tool row changes. Never hand-edit inside the markers; the next run overwrites it.

```
py build_bits.py            # rewrite the spans
py build_bits.py --check    # exit 1 if index.html is stale
```

The technology index (a by-tool lens over the same pieces) reads this same file when the corpus earns it — deferred until ~12–13 tagged pieces.

**Placeholders on inning pages:** a `<figure class="bit-figure">` holding a `div.placeholder-box` (dashed) stands in for a capture that hasn't landed. Swap the div for an `<img>` when the PNG lands in `assets/`; keep the figcaption. A `p.bit-game` line at the top of each inning is the game it leads with — Wax's pick; bracketed text there is a suggestion, not a ruling.
