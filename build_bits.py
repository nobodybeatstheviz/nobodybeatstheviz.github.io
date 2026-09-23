"""build_bits.py -- render the homepage card spans and the lineup pages' slot chrome from bits/pieces.json.

Source:        bits/pieces.json (hand-kept: one row per piece)
Analysis:      this script
Presentation:  two spans in index.html, between stable markers:

    <!-- LINEUP:START --> ... <!-- LINEUP:END -->   the batting order, 1 through 9
    <!-- AWAY:START -->   ... <!-- AWAY:END -->     the away games (Superstore)

               and, on each lineup page (bits/<slug>/index.html), everything
               that depends on the slot -- so a reorder is changing `n` and
               nothing else:

    KEEPING SCORE · <label> --  in <title>, og:title, twitter:title
    <span class="status-tag ..."> the marquee label
    <!-- NEXT:START --> ... <!-- NEXT:END -->   the on-deck line (next piece's question)
    <!-- NAV:START -->  ... <!-- NAV:END -->    prev · the lineup · next

    py build_bits.py            # rewrite the spans in place
    py build_bits.py --check    # exit 1 if any page would change (CI / pre-push)

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
        if played < len(rows):  # a full lineup needs no scoreboard line
            out.append(
                f'{INDENT}<p class="bit-grid-empty">{played} of {len(rows)} on wax. '
                f"The rest are on deck.</p>"
            )
    return "\n".join(out)


def splice(text: str, start: str, end: str, block: str, where: Path = PAGE) -> str:
    """Replace what sits between two markers; the end marker keeps the start marker's indent."""
    i = text.find(start)
    j = text.find(end)
    if i < 0 or j < 0 or j < i:
        sys.exit(f"markers {start} / {end} not found in {where.relative_to(HERE)} -- add them by hand once")
    indent = text[text.rfind("\n", 0, i) + 1 : i]
    return text[: i + len(start)] + "\n" + block + "\n" + indent + text[j:]


# ---- lineup pages: the slot chrome -------------------------------------------

NOTES_HREF = "../wax-baseball/"
LINEUP_HREF = "../../#the-lineup"


def lower_first(s: str) -> str:
    return s[0].lower() + s[1:]


def next_line(p: dict, nxt: dict | None, indent: str) -> str:
    if nxt is None:
        return (f'{indent}<p class="demo-caption">That\'s the game. <a href="{NOTES_HREF}">Back to the game notes</a>'
                f' &middot; <a href="{LINEUP_HREF}">the lineup &rarr;</a></p>')
    return (f'{indent}<p class="demo-caption">Next, {esc(lower_first(label(nxt)))}: '
            f'<a href="../{nxt["slug"]}/">{esc(nxt["question"])} &rarr;</a></p>')


def nav_line(prev: dict | None, nxt: dict | None, indent: str) -> str:
    left = (f'<a href="../{prev["slug"]}/">{esc(lower_first(label(prev)))}</a>' if prev
            else f'<a href="{NOTES_HREF}">the game notes</a>')
    right = (f'<a href="../{nxt["slug"]}/">{esc(lower_first(label(nxt)))}</a> &rarr;' if nxt
             else f'<a href="{NOTES_HREF}">the game notes</a>')
    return f'{indent}<p>&larr; {left} &middot; <a href="{LINEUP_HREF}">the lineup</a> &middot; {right}</p>'


def stamp_page(text: str, p: dict, prev: dict | None, nxt: dict | None, where: Path) -> str:
    lab = esc(label(p))
    text = re.sub(r"(KEEPING SCORE · )[^—<\"]*?( —)", rf"\g<1>{lab}\g<2>", text)
    text = re.sub(r'(<span class="status-tag [^"]*">)[^<]*(</span>)', rf"\g<1>{lab}\g<2>", text, count=1)
    ind = INDENT
    text = splice(text, "<!-- NEXT:START -->", "<!-- NEXT:END -->", next_line(p, nxt, ind), where)
    text = splice(text, "<!-- NAV:START -->", "<!-- NAV:END -->", nav_line(prev, nxt, ind), where)
    return text


def write_or_check(path: Path, old: str, new: str, check: bool, what: str) -> bool:
    """Returns True if the file is stale."""
    rel = path.relative_to(HERE)
    if new == old:
        return False
    if check:
        print(f"{rel}: stale -- run `py build_bits.py`")
        return True
    path.write_text(new, encoding="utf-8", newline="\n")
    print(f"{rel}: rewrote {what}")
    return False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="exit 1 if any page would change")
    args = ap.parse_args()

    pieces = json.loads(SOURCE.read_text(encoding="utf-8"))["pieces"]
    stale = False

    old = PAGE.read_text(encoding="utf-8")
    new = old
    for kind, (start, end) in SPANS.items():
        new = splice(new, start, end, render_span(kind, pieces))
    stale |= write_or_check(PAGE, old, new, args.check, "card spans")

    lineup = sorted((p for p in pieces if p["kind"] == "lineup"), key=lambda p: p["n"])
    if [p["n"] for p in lineup] != list(range(1, len(lineup) + 1)):
        sys.exit(f"lineup slots must be 1..{len(lineup)} with no gaps or repeats: {[p['n'] for p in lineup]}")
    for k, p in enumerate(lineup):
        prev = lineup[k - 1] if k > 0 else None
        nxt = lineup[k + 1] if k + 1 < len(lineup) else None
        path = HERE / "bits" / p["slug"] / "index.html"
        old = path.read_text(encoding="utf-8")
        stale |= write_or_check(path, old, stamp_page(old, p, prev, nxt, path), args.check, "slot chrome")

    if stale:
        sys.exit(1)
    if not args.check:
        print(f"up to date: index.html + {len(lineup)} lineup pages")


if __name__ == "__main__":
    main()
