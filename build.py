#!/usr/bin/env python3
"""Build the portfolio site from site.json and the notebooks it lists.

    python build.py            # published projects only  -> _site/
    python build.py --drafts   # also projects marked "draft": true

Notebooks are read with the outputs already saved in them; nothing is
re-run here. Run a notebook top to bottom and save it before you push.

Code-cell options go on the first lines of a cell, Quarto-style:

    #| hide            show the output, not the code
    #| collapse        start with the code folded
    #| hide-output     show the code, not the output
    #| skip            leave the whole cell off the page
    #| label: Pass rate          label for a single-number result
    #| caption: What the chart shows   caption under a chart or table
"""

import argparse
import base64
import html
import json
import re
import shutil
import sys
from pathlib import Path

import markdown
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound

ROOT = Path(__file__).parent
OUT = ROOT / "_site"
TEMPLATES = ROOT / "templates"

VEGA = {
    "vega": "https://cdn.jsdelivr.net/npm/vega@6.4.0",
    "vega-lite": "https://cdn.jsdelivr.net/npm/vega-lite@6.4.3",
    "vega-embed": "https://cdn.jsdelivr.net/npm/vega-embed@7.3.0",
}
KATEX = "https://cdn.jsdelivr.net/npm/katex@0.16.22/dist"

LONG_CODE = 18  # cells longer than this start folded to a preview
SCALAR_MAX = 40  # a one-line result up to this long becomes a result card

esc = html.escape


# ---------- templates ----------

def render(template, **values):
    text = (TEMPLATES / template).read_text()
    return re.sub(r"\{\{\s*(\w+)\s*\}\}", lambda m: str(values.get(m.group(1), "")), text)


# ---------- markdown with math kept intact ----------

MATH = re.compile(r"(\$\$.+?\$\$|\\\[.+?\\\]|(?<![\\$])\$(?!\s)[^$\n]+?(?<!\s)\$)", re.S)


def md_to_html(source):
    stash = []

    def keep(m):
        stash.append(m.group(0))
        return f"MATHSTASH{len(stash) - 1}X"

    # \$ is a literal dollar sign (as in Jupyter), never a math delimiter.
    protected = MATH.sub(keep, source.replace("\\$", "DOLLARSIGNX"))
    md = markdown.Markdown(
        extensions=["fenced_code", "tables", "toc", "sane_lists", "codehilite"],
        extension_configs={
            "codehilite": {"css_class": "hl", "guess_lang": False},
            "toc": {"permalink": False},
        },
    )
    out = md.convert(protected)
    out = re.sub(r"MATHSTASH(\d+)X", lambda m: esc(stash[int(m.group(1))], quote=False), out)
    out = out.replace("DOLLARSIGNX", '<span class="usd">$</span>')
    out = label_table_cells(out)
    return out, md.toc_tokens, bool(stash)


def label_table_cells(html_text):
    """Give each table cell its column name, so narrow screens can stack rows as cards."""
    def one(table):
        heads = [re.sub(r"<[^>]+>", "", h).strip() for h in re.findall(r"<th[^>]*>(.*?)</th>", table.group(0), re.S)]
        if not heads:
            return table.group(0)
        def row(r):
            cells = iter(heads)
            return re.sub(r"<td(?=[\s>])", lambda m: f'<td data-label="{esc(next(cells, ""))}"', r.group(0))
        return re.sub(r"<tr>.*?</tr>", row, table.group(0), flags=re.S)
    return re.sub(r"<table>.*?</table>", one, html_text, flags=re.S)


# ---------- code ----------

def parse_options(source):
    opts, lines = {}, source.split("\n")
    while lines and lines[0].startswith("#|"):
        body = lines.pop(0)[2:].strip()
        key, _, val = body.partition(":")
        opts[key.strip().lower()] = val.strip() or True
    return opts, "\n".join(lines).strip("\n")


def highlight_code(code, language):
    try:
        lexer = get_lexer_by_name(language)
    except ClassNotFound:
        lexer = get_lexer_by_name("text")
    return highlight(code, lexer, HtmlFormatter(nowrap=True))


def code_block(code, language, collapsed):
    n = code.count("\n") + 1
    state = "folded" if collapsed else ("preview" if n > LONG_CODE else "open")
    label = {"python": "Python", "r": "R"}.get(language, language)
    return f"""
<div class="code" data-state="{state}" data-lines="{n}">
  <div class="code-bar">
    <span class="code-lang">{esc(label)}</span>
    <span class="code-actions">
      <button class="code-toggle" type="button"></button>
    </span>
  </div>
  <pre class="hl"><code>{highlight_code(code, language)}</code></pre>
</div>"""


# ---------- outputs ----------

ANSI = re.compile(r"\x1b\[[0-9;]*m")
NUMPY_SCALAR = re.compile(r"^np\.\w+\((.*)\)$")


def vega_spec(data):
    """The Vega-Lite spec of an Altair chart, whichever way the notebook saved it."""
    for mime, value in data.items():
        if mime.startswith("application/vnd.vegalite.v"):
            return value
    page = text_of(data.get("text/html", ""))
    if "vega-embed" not in page or "schema/vega-lite" not in page:
        return None
    # Altair's HTML renderer ends with  ...})({spec}, {"mode": "vega-lite"});
    start = page.rfind("})({")
    if start < 0:
        return None
    try:
        spec, _ = json.JSONDecoder().raw_decode(page, start + 3)
    except ValueError:
        return None
    return spec if "$schema" in spec else None


def merge_index_header(table):
    """pandas puts a named index on its own header row; fold it into the row above."""
    m = re.search(r"<thead>\s*<tr[^>]*>(.*?)</tr>\s*<tr[^>]*>(.*?)</tr>\s*</thead>", table, re.S)
    if not m:
        return table
    second = re.findall(r"<th[^>]*>(.*?)</th>", m.group(2), re.S)
    if not second or any(c.strip() for c in second[1:]):
        return table
    first = re.sub(r"<th[^>]*>\s*</th>", f'<th class="idx">{second[0]}</th>', m.group(1), count=1)
    return table[:m.start()] + f"<thead><tr>{first}</tr></thead>" + table[m.end():]


def tabular(text):
    """Column-aligned output (tables, model summaries) keeps its layout and scrolls sideways;
    everything else wraps."""
    aligned = re.search(r"\S {2,}\S", text) or re.search(r"^[=\-]{8,}$", text, re.M)
    return " tabular" if aligned else ""


def text_of(value):
    return "".join(value) if isinstance(value, list) else value


class Outputs:
    def __init__(self, slug, out_dir):
        self.slug, self.out_dir = slug, out_dir
        self.figures = 0
        self.charts = 0

    def save_image(self, data, ext):
        self.figures += 1
        name = f"fig-{self.figures}.{ext}"
        raw = data.encode() if ext == "svg" else base64.b64decode(data)
        (self.out_dir / name).write_bytes(raw)
        return name

    def render(self, output, opts):
        kind = output.get("output_type")
        caption = opts.get("caption")
        cap = f'<figcaption>{esc(caption)}</figcaption>' if isinstance(caption, str) else ""

        if kind == "stream":
            text = ANSI.sub("", text_of(output.get("text", ""))).rstrip()
            if not text:
                return ""
            cls = "out-text err" if output.get("name") == "stderr" else "out-text"
            return f'<pre class="{cls}{tabular(text)}">{esc(text)}</pre>'

        if kind == "error":
            print(f"  ! {self.slug}: a cell raised {output.get('ename')}; left off the page", file=sys.stderr)
            return ""

        data = output.get("data", {})
        spec = vega_spec(data)
        if spec is not None:
            self.charts += 1
            spec = json.dumps(spec).replace("</", "<\\/")
            return (f'<figure class="out-chart"><div class="chart" data-chart>'
                    f'<script type="application/json">{spec}</script></div>{cap}</figure>')

        if "image/svg+xml" in data:
            name = self.save_image(text_of(data["image/svg+xml"]), "svg")
            return f'<figure class="out-figure"><img src="{name}" alt="{esc(caption or "Figure")}" loading="lazy">{cap}</figure>'
        for mime, ext in (("image/png", "png"), ("image/jpeg", "jpg")):
            if mime in data:
                name = self.save_image(text_of(data[mime]), ext)
                return f'<figure class="out-figure"><img src="{name}" alt="{esc(caption or "Figure")}" loading="lazy">{cap}</figure>'

        if "text/html" in data:
            table = text_of(data["text/html"])
            table = re.sub(r"<style.*?</style>", "", table, flags=re.S)
            table = re.sub(r'\s(border="\d+"|class="dataframe")', "", table)
            table = table.replace("<table", '<table class="df"', 1)
            table = merge_index_header(table)
            return f'<figure class="out-table"><div class="table-scroll">{table}</div>{cap}</figure>'

        if "text/plain" in data:
            text = ANSI.sub("", text_of(data["text/plain"])).strip()
            text = NUMPY_SCALAR.sub(r"\1", text)  # np.float64(0.746) -> 0.746
            if kind == "execute_result" and "\n" not in text and len(text) <= SCALAR_MAX:
                label = opts.get("label")
                lab = f'<span class="result-label">{esc(label)}</span>' if isinstance(label, str) else ""
                return f'<div class="out-result">{lab}<span class="result-value">{esc(text.strip(chr(39)))}</span></div>'
            return f'<pre class="out-text{tabular(text)}">{esc(text)}</pre>'

        return ""


# ---------- pages ----------

def build_project(project, site, drafts):
    slug = project["slug"]
    nb_path = ROOT / project["notebook"]
    nb = json.loads(nb_path.read_text())
    language = (nb.get("metadata", {}).get("kernelspec", {}).get("language")
                or nb.get("metadata", {}).get("language_info", {}).get("name") or "python").lower()

    out_dir = OUT / "projects" / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs = Outputs(slug, out_dir)

    blocks, toc, uses_math = [], [], False
    for cell in nb["cells"]:
        source = text_of(cell.get("source", ""))
        if cell["cell_type"] == "markdown":
            body, tokens, has_math = md_to_html(source)
            uses_math |= has_math
            toc += [t for t in tokens if t["level"] == 2]
            blocks.append(f'<div class="prose reveal">{body}</div>')
        elif cell["cell_type"] == "code":
            opts, code = parse_options(source)
            if opts.get("skip"):
                continue
            parts = []
            if code.strip() and not opts.get("hide"):
                parts.append(code_block(code, language, bool(opts.get("collapse"))))
            if not opts.get("hide-output"):
                parts += [outputs.render(o, opts) for o in cell.get("outputs", [])]
            parts = [p for p in parts if p]
            if parts:
                blocks.append(f'<section class="cell reveal">{"".join(parts)}</section>')

    toc_html = "".join(f'<a href="#{t["id"]}">{esc(t["name"])}</a>' for t in toc)
    scripts = []
    if outputs.charts:
        scripts += [f'<script src="{u}" defer></script>' for u in VEGA.values()]
        scripts.append('<script src="../../assets/charts.js" defer></script>')
    head_extra = ""
    if uses_math:
        head_extra = f'<link rel="stylesheet" href="{KATEX}/katex.min.css">'
        scripts += [f'<script src="{KATEX}/katex.min.js" defer></script>',
                    f'<script src="{KATEX}/contrib/auto-render.min.js" defer></script>']

    lang_label = {"python": "Python", "r": "R"}.get(language, language)
    tags = "".join(f'<span class="tag">{esc(t)}</span>' for t in project.get("tags", [])
                   if t.lower() != lang_label.lower())
    page = render(
        "project.html",
        title=esc(project["title"]),
        site_name=esc(site["name"]),
        summary=esc(project.get("summary", "")),
        slug=slug,
        tags=tags,
        date=esc(project.get("date", "")),
        language={"python": "Python", "r": "R"}.get(language, language),
        toc=toc_html,
        toc_class="" if toc else "no-toc",
        body="\n".join(blocks),
        head_extra=head_extra,
        credits=credits_html(site),
        scripts="\n".join(scripts),
    )
    (out_dir / "index.html").write_text(page)
    print(f"  built projects/{slug}/  ({outputs.charts} charts, {outputs.figures} images)")


def credits_html(site):
    parts = [f'{esc(c["role"])} set in <a class="credit" href="{esc(c["url"])}" target="_blank" rel="noopener">'
             f'{esc(c["font"])}</a> by {esc(c["by"])}' for c in site.get("credits", [])]
    return f"<p>{'. '.join(parts)}.</p>" if parts else ""


def build_home(site, projects):
    cards = []
    for i, p in enumerate(projects):
        tags = "".join(f'<span class="tag">{esc(t)}</span>' for t in p.get("tags", []))
        draft = '<span class="tag tag-draft">Draft</span>' if p.get("draft") else ""
        cards.append(f"""
<a class="card reveal" href="projects/{p['slug']}/" style="--i:{i}">
  <div class="card-tags">{draft}{tags}</div>
  <h3>{esc(p['title'])}</h3>
  <p>{esc(p.get('summary', ''))}</p>
  <div class="card-foot"><span>{esc(p.get('date', ''))}</span><span class="card-go">Read the project <span aria-hidden="true">&rarr;</span></span></div>
</a>""")
    if not cards:
        cards.append('<p class="empty">First project coming soon.</p>')
    links = "".join(f'<a href="{esc(l["url"])}" rel="me noopener">{esc(l["label"])}</a>' for l in site.get("links", []))
    bio = "".join(f"<p>{esc(p)}</p>" for p in site.get("bio", []))
    def linked(text, url, cls=""):
        attrs = f' class="{cls}"' if cls else ""
        if not url:
            return f"<span{attrs}>{esc(text)}</span>"
        return f'<a{attrs} href="{esc(url)}" target="_blank" rel="noopener">{esc(text)}</a>'

    edu = "".join(
        f'<li><span class="edu-degree">{linked(e["degree"], e.get("url"))}</span>'
        f'<span class="edu-school">{linked(e["school"], e.get("school_url"))}</span>'
        f'<span class="edu-year">{esc(e.get("year", ""))}</span>'
        + (f'<span class="edu-note">Minor{linked(e["minor"], e.get("minor_url"), "edu-chip")}</span>' if e.get("minor") else "")
        + "</li>"
        for e in site.get("education", []))
    edu = (f'<section class="home-section edu-section" aria-labelledby="edu-h">'
           f'<h2 id="edu-h" class="section-label">Education</h2>'
           f'<div class="edu-card"><ul class="edu">{edu}</ul></div></section>') if edu else ""
    page = render("home.html", credits=credits_html(site), name=esc(site["name"]), role=esc(site.get("role", "")),
                  bio=bio, education=edu, links=links, cards="".join(cards), count=len(projects))
    (OUT / "index.html").write_text(page)
    print("  built index.html")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drafts", action="store_true", help="include projects marked as drafts")
    args = ap.parse_args()

    site = json.loads((ROOT / "site.json").read_text())
    projects = [p for p in site["projects"] if args.drafts or not p.get("draft")]

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "assets", OUT / "assets")
    (OUT / ".nojekyll").touch()

    for p in projects:
        build_project(p, site, args.drafts)
    build_home(site, projects)


if __name__ == "__main__":
    main()
