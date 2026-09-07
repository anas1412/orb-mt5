# One-off studies

The scripts behind `../FINDINGS.md`: parameter sweeps, session comparisons,
filter and stop experiments, the early equity and pass-rate models. None of them
is part of the pipeline -- `../../update.sh` and the `build_*.py` / `report_data.py`
family never import them -- and most were superseded by what they taught.

They are kept because the findings cite them. They still run, from this folder,
with the pipeline helpers on the path:

    PYTHONPATH=.. python3 sweep.py

`report.html` is the pre-Pages report from August 2026, kept for the record.
