# What 798 Films Say About Representation and Revenue

DSC 530 final project: does a film's Bechdel test result relate to its box office performance once budget and release year are held fixed?

- `notebooks/bechdel_portfolio.ipynb`: the condensed, narrative version shown on the portfolio site.
- `notebooks/DSC_530_FinalProject_McKee.ipynb`: the full final project notebook.
- `notebooks/00_ingest.ipynb` … `07_conclusions.ipynb`: the pipeline that builds the analysis table (ingest, per-source EDA, mirror union, cleaning, fuzzy join, analysis spec, models, conclusions).
- `DSC_530_FinalProject_Narrative_McKee.md`: the written narrative.
- `data/raw/`: source files as acquired; see `data/raw/README_provenance.md`.
- `data/interim/`: the cleaned and joined tables, including `analysis_table.csv` (798 films) and its data dictionary.
- `figures/`: static figures saved by the notebooks.

Run the notebooks from inside `notebooks/` (they read `../data/...`). Dependencies are in `requirements.txt`.
