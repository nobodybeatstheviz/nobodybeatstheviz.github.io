"""build_print.py -- flatten every page of the site into one printable Markdown doc.

Source:        index.html + bits/*/index.html (the pages themselves)
               bits/pieces.json (the reading order for the lineup)
Analysis:      this script
Presentation:  site-review.md (gitignored -- a printout for pen markup, never edited)

    py build_print.py                 # write site-review.md
    py build_print.py -o some.md      # write elsewhere

Order: homepage, then the pieces as the homepage shows them (game notes,
the lineup by slot n, away games), then any bit not in pieces.json,
alphabetically.
Each page opens with its live URL and closes with a ruled Notes block.
Homepage cards compact to one bullet each. Images become a one-line note
(alt text) plus their caption; scripts, styles and the analytics beacon
are dropped. Stdlib only.
"""

import argparse
import json
import re
import subprocess
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
PIECES = HERE / "bits" / "pieces.json"
SITE = "https://nobodybeatstheviz.com/"

SKIP = {"script", "style", "head", "title", "meta", "link", "noscript"}
BLOCK = {"p", "div", "section", "header", "footer", "main", "article", "figure",
         "figcaption", "ul", "ol", "li", "table", "thead", "tbody", "tr", "hr",
         "blockquote", "pre", "h1", "h2", "h3", "h4", "h5", "h6", "iframe"}
HEADINGS = {"h1": "##", "h2": "###", "h3": "####", "h4": "#####"}  # page title is the doc's h1


def absolute(href: str) -> str:
    """Relative site links -> live URLs, so the printout can be typed back in."""
    if href.startswith("../../"):
        return SITE + href[6:]
    if href.startswith("../"):
        return SITE + "bits/" + href[3:]
    if href.startswith(("#", "bits/", "assets/")):
        return SITE + href
    return href


class ToMarkdown(HTMLParser):
    """Walk one page's body and emit Markdown. Small vocabulary, no surprises."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []            # finished lines
        self.buf = []            # inline text of the block being built
        self.skip = 0            # depth inside a SKIP tag
        self.in_body = False
        self.in_pre = False
        self.lists = []          # stack of [kind, counter]
        self.li_prefix = ""
        self.heading = "##"
        self.link = None         # href of the open <a>, or None
        self.link_mark = 0       # index in buf where its "[" sits
        self.card = 0            # nesting depth inside a homepage .bit-card
        self.badge_open = False
        self.status_open = False
        self.drop_next_text = False
        self.table = None        # rows while inside <table>
        self.row = None
        self.cell = None
        self.is_header_row = False

    # -- helpers -----------------------------------------------------------

    def flush(self, prefix=""):
        text = "".join(self.buf)
        self.buf = []
        if self.in_pre:
            self.out.append(text)
            return
        text = re.sub(r"[ \t]*\n[ \t]*", " ", text)
        text = re.sub(r" {2,}", " ", text).strip()
        if text:
            self.out.append(prefix + text)
            self.out.append("")

    def text(self, s):
        if self.cell is not None:
            self.cell.append(s)
        else:
            self.buf.append(s)

    def open_link(self, href):
        self.link = href
        self.link_mark = len(self.buf)
        self.text("[")

    def close_link(self):
        if self.link is None:
            return
        href, self.link = self.link, None
        inner = "".join(self.buf[self.link_mark + 1:]).strip()
        if inner:
            self.text(f"]({absolute(href)})")
        else:                       # empty anchor: nothing to print
            del self.buf[self.link_mark:]

    def close_card_part(self):
        if self.badge_open:
            self.text("**")
            self.badge_open = False
        self.card -= 1
        if self.card == 0:
            self.flush("- ")

    # -- parser callbacks --------------------------------------------------

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "body":
            self.in_body = True
            return
        if not self.in_body:
            return
        if tag in SKIP:
            self.skip += 1
            return
        if self.skip:
            return
        cls = a.get("class", "").split()

        # Homepage cards: everything inside one card joins into one bullet.
        if "bit-card" in cls:
            self.flush()
            self.card = 1
            if tag == "a":
                self.open_link(a.get("href", ""))
            return
        if self.card and tag in ("div", "p"):
            if tag == "div":
                self.card += 1
            if "".join(self.buf).strip() not in ("", "["):
                self.text(" · ")
            if "bit-badge" in cls:
                self.text("**")
                self.badge_open = True
            return

        if tag in HEADINGS:
            self.flush()
            self.heading = HEADINGS[tag]
        elif tag == "p":
            self.flush()
            if "hook" in cls:
                self.buf.append("> ")
        elif tag in ("ul", "ol"):
            self.flush()
            self.lists.append([tag, 0])
        elif tag == "li":
            self.flush()
            kind, n = self.lists[-1]
            self.lists[-1][1] = n + 1
            indent = "  " * (len(self.lists) - 1)
            self.li_prefix = f"{indent}{n + 1}. " if kind == "ol" else f"{indent}- "
        elif tag in ("strong", "b"):
            self.text("**")
        elif tag in ("em", "i"):
            self.text("*")
        elif tag == "code" and not self.in_pre:
            self.text("`")
        elif tag == "pre":
            self.flush()
            self.in_pre = True
            self.out.append("```")
        elif tag == "a":
            self.open_link(a.get("href", ""))
        elif tag == "img":
            if self.link is not None:       # a linked image: drop the link, keep the note
                del self.buf[self.link_mark:]
                self.link = None
            self.flush()
            self.out += [f"*[image: {a.get('alt', '').strip()}]*", ""]
        elif tag == "br":
            self.text("  \n")
        elif tag == "hr":
            self.flush()
            self.out += ["---", ""]
        elif tag == "blockquote":
            self.flush()
            self.buf.append("> ")
        elif tag == "table":
            self.flush()
            self.table = []
        elif tag == "tr":
            self.row = []
            self.is_header_row = False
        elif tag in ("td", "th"):
            self.cell = []
            if tag == "th":
                self.is_header_row = True
        elif tag == "iframe":
            self.flush()
            self.out += [f"*[embedded frame: {a.get('src', '')}]*", ""]
        elif tag == "span" and ("hash" in cls or "dash" in cls):
            self.drop_next_text = True
        elif tag == "span" and "status-tag" in cls:
            self.text("`")
            self.status_open = True
        elif tag in BLOCK:
            self.flush()

    def handle_endtag(self, tag):
        if not self.in_body:
            return
        if tag in SKIP:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return

        if self.card and tag in ("div", "p", "a"):
            if tag == "a":
                self.close_link()
            if tag in ("div", "a"):
                self.close_card_part()
            return

        if tag in HEADINGS:
            self.flush(self.heading + " ")
        elif tag == "p":
            self.flush()
        elif tag == "li":
            self.flush(self.li_prefix)
            self.out.pop()          # no blank line between list items
        elif tag in ("ul", "ol"):
            self.flush()
            self.lists.pop()
            if not self.lists:
                self.out.append("")
        elif tag in ("strong", "b"):
            self.text("**")
        elif tag in ("em", "i"):
            self.text("*")
        elif tag == "code" and not self.in_pre:
            self.text("`")
        elif tag == "pre":
            self.flush()
            self.out += ["```", ""]
            self.in_pre = False
        elif tag == "a":
            self.close_link()
        elif tag == "span" and self.status_open:
            self.text("` ")
            self.status_open = False
        elif tag == "figcaption":
            self.flush("*Caption:* ")
        elif tag in ("td", "th"):
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr":
            self.table.append((self.is_header_row, self.row))
            self.row = None
        elif tag == "table":
            self.emit_table()
            self.table = None
        elif tag in BLOCK:
            self.flush()

    def handle_data(self, data):
        if not self.in_body or self.skip:
            return
        if self.drop_next_text:
            self.drop_next_text = False
            return
        self.text(data)

    def emit_table(self):
        rows = self.table
        if not rows:
            return
        width = max(len(r) for _, r in rows)
        if not rows[0][0]:
            rows.insert(0, (True, [""] * width))
        for i, (_, cells) in enumerate(rows):
            cells = cells + [""] * (width - len(cells))
            self.out.append("| " + " | ".join(cells) + " |")
            if i == 0:
                self.out.append("|" + "---|" * width)
        self.out.append("")

    def result(self):
        self.flush()
        text = "\n".join(self.out)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip() + "\n"


def convert(path: Path) -> tuple[str, str]:
    html = path.read_text(encoding="utf-8")
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    title = " ".join(m.group(1).split()) if m else path.parent.name
    title = title.replace(" · Nobody Beats the Viz", "").strip()
    p = ToMarkdown()
    p.feed(html)
    return title, p.result()


def page_order() -> list[Path]:
    order = [HERE / "index.html"]
    seen = set()
    pieces = json.loads(PIECES.read_text(encoding="utf-8"))["pieces"]
    rank = {"notes": 0, "lineup": 1, "away": 2}
    for p in sorted(pieces, key=lambda p: (rank.get(p["kind"], 3), p["n"])):
        d = HERE / "bits" / p["slug"] / "index.html"
        if d.exists():
            order.append(d)
            seen.add(d)
    for d in sorted((HERE / "bits").glob("*/index.html")):
        if d not in seen:
            order.append(d)
    return order


def git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       cwd=HERE, text=True).strip()
    except Exception:
        return "?"


NOTES = "\n".join(["**Notes**", ""] + ["&nbsp;", ""] * 6)


def build() -> str:
    pages = page_order()
    doc = ["# nobodybeatstheviz.com — print review", "",
           f"*Generated {date.today().isoformat()} from commit `{git_head()}` by "
           f"`build_print.py`. {len(pages)} pages. Mark it up; changes go back into "
           "the HTML, never here.*", "",
           "## Contents", ""]
    bodies = []
    for i, path in enumerate(pages, 1):
        title, md = convert(path)
        rel = path.relative_to(HERE).as_posix()
        url = SITE if rel == "index.html" else SITE + rel[: -len("index.html")]
        doc.append(f"{i}. {title}")
        bodies.append("\n".join([
            '<div style="page-break-before: always"></div>', "",
            f"# {i}. {title}", "",
            f"`{url}` · source `{rel}`", "",
            md,
            NOTES,
        ]))
    doc.append("")
    return "\n".join(doc) + "\n" + "\n\n".join(bodies)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", type=Path, default=HERE / "site-review.md")
    args = ap.parse_args()
    args.out.write_text(build(), encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
