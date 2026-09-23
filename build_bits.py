"""build_bits.py -- render the homepage card spans from bits/pieces.json.

Source:        bits/pieces.json (hand-kept: one row per piece)
Analysis:      this script
Presentation:  two spans in index.html, between stable markers:

    <!-- LINEUP:START --> ... <!-- LINEUP:END -->   the batting order, 1 through 9
    <!-- AWAY:START -->   ... <!-- AWAY:END -->     the away games (Superstore)

    py build_bits.py            # rewrite the spans in place
    py build_bits.py --check    # exit 1 if index.html would change (CI / pre-push)

A piece with a url renders as a link card; without one it renders as a
non-link slot (`div.bit-card.wip`). Status "on-wax" is earned-only -- set it
in the Source when the piece is done, never here. A lineup row's label is
derived from its slot `n` (SLOT_LABELS below), never typed in the Source, so
a reorder relabels itself. Output is idempotent.
No markers -> it refuses and says so; adding them is a one-time hand step.
Stdlib only.
"""

import argparse
import html
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "bits" / "pieces.json"
PAGE = HERE / "index.html"

SPANS = {
    "lineup": ("<!-- LINEUP:START -->", "<!-- LINEUP:END -->"),
    "away": ("<!-- AWAY:START -->", "<!-- AWAY:END -->"),
}
INDENT = "      "

# PA-announcer style (ruled 2026-09-23, provisional -- may go hybrid with the
# spot nicknames once the pieces are slotted).
SLOT_LABELS = {
    1: "Leading off",
    2: "Batting 2nd",
    3: "Batting 3rd",
    4: "Batting cleanup",
    5: "Batting 5th",
    6: "Batting 6th",
    7: "Batting 7th",
    8: "Batting 8th",
    9: "Batting 9th",
}


def label(p: dict) -> str:
    return SLOT_LABELS[p["n"]] if p["kind"] == "lineup" else p["label"]


def esc(s: str) -> str:
    return html.escape(s, quote=False)


def title_html(s: str) -> str:
    """[[word]] -> <span>word</span> (the gold word), everything else escaped."""
    parts = re.split(r"(\[\[.*?\]\])", s)
    out = []
    for p in parts:
        if p.startswith("[[") and p.endswith("]]"):
            out.append(f"<span>{esc(p[2:-2])}</span>")
        else:
            out.append(esc(p))
    return "".join(out)


def card(p: dict) -> str:
    kind = p["kind"]
    url = p.get("url", "")
    status = p.get("status", "wip")
    classes = ["bit-card"]
    if kind == "lineup":
        classes.append("baseball")
    if not url:
        classes.append("wip")
    cls = " ".join(classes)
    tag = "a" if url else "div"
    href = f' href="{esc(url)}"' if url else ""

    lines = [f'{INDENT}<{tag} class="{cls}"{href}>']
    lines.append(f'{INDENT}  <div class="bit-badge">{esc(label(p))}</div>')
    lines.append(f'{INDENT}  <div class="bit-title">{title_html(p["question"])}</div>')
    if p.get("title"):
        lines.append(f'{INDENT}  <div class="bit-tagline">{esc(p["title"])}</div>')
    if p.get("blurb"):
        lines.append(f'{INDENT}  <p class="bit-blurb">{esc(p["blurb"])}</p>')
    lines.append(f'{INDENT}  <div class="bit-tags">')
    status_word = "on wax" if status == "on-wax" else "WIP"
    lines.append(f'{INDENT}    <span class="bit-tag status {status}">{status_word}</span>')
    for t in p.get("tools", []):
        lines.append(f'{INDENT}    <span class="bit-tag">{esc(t)}</span>')
    lines.append(f"{INDENT}  </div>")
    lines.append(f"{INDENT}</{tag}>")
    return "\n".join(lines)


def render_span(kind: str, pieces: list) -> str:
    rows = sorted((p for p in pieces if p["kind"] == kind), key=lambda p: p["n"])
    body = "\n\n".join(card(p) for p in rows)
    out = [f'{INDENT}<div class="bit-grid">', body, f"{INDENT}</div>"]
    if kind == "lineup":
        played = sum(1 for p in rows if p.get("status") == "on-wax")
        out.append(
            f'{INDENT}<p class="bit-grid-empty">{played} of {len(rows)} on wax. '
            f"The rest are on deck.</p>"
        )
    return "\n".join(out)


def splice(text: str, start: str, end: str, block: str) -> str:
    i = text.find(start)
    j = text.find(end)
    if i < 0 or j < 0 or j < i:
        sys.exit(f"markers {start} / {end} not found in {PAGE.name} -- add them by hand once")
    return text[: i + len(start)] + "\n" + block + "\n" + INDENT + text[j:]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="exit 1 if the page would change")
    args = ap.parse_args()

    pieces = json.loads(SOURCE.read_text(encoding="utf-8"))["pieces"]
    old = PAGE.read_text(encoding="utf-8")
    new = old
    for kind, (start, end) in SPANS.items():
        new = splice(new, start, end, render_span(kind, pieces))

    if new == old:
        print(f"{PAGE.name}: up to date")
        return
    if args.check:
        sys.exit(f"{PAGE.name}: stale -- run `py build_bits.py`")
    PAGE.write_text(new, encoding="utf-8", newline="\n")
    n_lineup = sum(1 for p in pieces if p["kind"] == "lineup")
    n_away = sum(1 for p in pieces if p["kind"] == "away")
    print(f"{PAGE.name}: rewrote spans ({n_lineup} in the lineup, {n_away} away games)")


if __name__ == "__main__":
    main()
