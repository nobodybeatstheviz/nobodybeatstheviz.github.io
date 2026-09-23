# nobodybeatstheviz.com

The personal site of George "Wax" Weatherwax — NBTV, The Viz, P3 stage.

Static HTML/CSS, deployed via GitHub Pages from `main`.

- **Homepage:** [`index.html`](index.html) — hero → the game notes → the lineup (the batting order, 1 through 9) → the away games → who keeps score → footer. The shape and the copy rulings live in the wax-system repo (`nbtv-brand/website-positioning.md`, `the-viz-persona.md`).
- **Bits:** [`bits/`](bits/) — one folder per piece. `bits/wax-baseball/` is the game notes (before first pitch). Lineup slugs name the piece, never the slot (`bits/bar-chart/`, not `bits/leadoff/`) — a reorder changes `n` in the Source and moves no URL.
- **Logo + brand assets** live in the parent Wax-System Drive folder, not in this repo.

## Build

The site has one generated span. Everything else is hand-authored HTML.

- **Source:** [`bits/pieces.json`](bits/pieces.json) — one row per piece (the lineup, away games, the notes): slot `n`, question, working title, tools, status, url, date. Lineup rows carry no label — the generator derives it from `n` (Leading off, Batting 2nd … Batting cleanup …).
- **Generator:** [`build_bits.py`](build_bits.py) — renders the lineup and away-games card grids into `index.html` between `<!-- LINEUP:START/END -->` and `<!-- AWAY:START/END -->`, and stamps each lineup page's slot chrome: the label in `<title>`/og/twitter and the status tag, the on-deck line (`<!-- NEXT:START/END -->` — the next piece's card question), and the prev/next nav (`<!-- NAV:START/END -->`). A reorder is changing `n`; the generator refuses slots with gaps or repeats. Stdlib only, idempotent.
- **When to run:** after any edit to `pieces.json` — a piece lands (set `url`, `date`, `status: on-wax`), the order changes (`n`), a question is reworded, a tool row changes. Never hand-edit inside the markers or the slot labels; the next run overwrites them. The on-deck teaser *is* the next piece's `question` — reword it there.

```
py build_bits.py            # rewrite the spans
py build_bits.py --check    # exit 1 if index.html is stale
```

The technology index (a by-tool lens over the same pieces) reads this same file when the corpus earns it — deferred until ~12–13 tagged pieces.

**Print review:** [`build_print.py`](build_print.py) — flattens every page (`index.html` + `bits/*/index.html`) into one Markdown doc, `site-review.md`, for offline read-and-markup in pen. Gitignored — a printout, regenerated on demand, never edited or committed.

```
py build_print.py            # write site-review.md
```

**Placeholders on lineup pages:** a `<figure class="bit-figure">` holding a `div.placeholder-box` (dashed) stands in for a capture that hasn't landed. Swap the div for an `<img>` when the PNG lands in `assets/`; keep the figcaption. A `p.bit-game` line at the top of each lineup page is the game it leads with — Wax's pick; bracketed text there is a suggestion, not a ruling.
