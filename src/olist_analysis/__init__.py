"""``olist_analysis`` - reusable analysis toolbox for the Olist e-commerce project.

The package holds every computation that is reused across the notebooks:

* :mod:`olist_analysis.config` - portable paths, table metadata, analysis contracts
* :mod:`olist_analysis.data_loader` - raw CSV loading plus parquet cache
* :mod:`olist_analysis.data_quality` - missingness, key, referential integrity probes
* :mod:`olist_analysis.cleaning` - documented, reproducible cleaning pipeline
* :mod:`olist_analysis.features` - derived business features (delivery, delay, time keys)
* :mod:`olist_analysis.metrics` - the business metrics required by the course brief
* :mod:`olist_analysis.plotting` - Persian-aware, consistently styled charts
* :mod:`olist_analysis.reporting` - executive report (Markdown + PDF)
* :mod:`olist_analysis.pipeline` - runs every analysis and persists results
"""

__version__ = "1.0.0"
