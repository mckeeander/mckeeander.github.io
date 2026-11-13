# mckeeander.github.io

My data science portfolio. Each project page is built from a Jupyter notebook: markdown cells become the write-up, code cells become syntax-highlighted code, and their saved outputs (numbers, tables, Altair charts, matplotlib figures) appear underneath.

## Adding a project

1. Put the notebook in `notebooks/`, run it top to bottom, and **save it with its outputs**. The build doesn't re-run notebooks.
2. Add an entry to `projects` in `site.json`:
   ```json
   { "slug": "bechdel", "notebook": "notebooks/bechdel.ipynb",
     "title": "…", "summary": "…", "tags": ["…"], "date": "2026-11" }
   ```
   Add `"draft": true` to keep it off the live site while you work on it.
3. Push to `main`. The GitHub Action builds the site and publishes it.

## Cell options

Put these on the first lines of a code cell:

| Option | Effect |
|---|---|
| `#| hide` | show the output, not the code |
| `#| collapse` | code starts folded behind "Show code" |
| `#| hide-output` | show the code, not the output |
| `#| skip` | leave the cell off the page |
| `#| label: Correlation` | label shown on a single-number result |
| `#| caption: …` | caption under a chart, figure or table |

Code cells longer than 18 lines start as a preview with "Show all lines".

Charts: Altair charts become interactive and pick up the site's dark theme automatically. For matplotlib, use `plt.style.use("portfolio.mplstyle")` (in `notebooks/`). Math in markdown (`$r$`, `$$…$$`) is rendered with KaTeX.

## Previewing locally

```sh
pip install -r requirements.txt
python build.py --drafts        # includes draft projects
python -m http.server -d _site  # open http://localhost:8000
```
