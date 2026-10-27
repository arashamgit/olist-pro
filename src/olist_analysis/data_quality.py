"""Reusable data-quality probes.

Every function returns a plain DataFrame (or dict of scalars) so results can be
written to ``reports/tables/`` and pasted into documentation without
re-formatting.  Nothing here mutates its input: the raw frames stay untouched.
"""

from __future__ import annotations

import pandas as pd

from .config import RAW_TABLES


def column_profile(frame: pd.DataFrame, table_name: str) -> pd.DataFrame:
    """Per-column dtype / missingness / cardinality profile.

    ``sample_values`` shows up to three real distinct values so that a reader
    (and the data dictionary) can see what the column actually contains.
    """
    total = len(frame)
    rows = []
    for column in frame.columns:
        series = frame[column]
        n_missing = int(series.isna().sum())
        non_null = series.dropna()
        samples = [str(v) for v in non_null.unique()[:3]]
        rows.append(
            {
                "table": table_name,
                "column": column,
                "dtype": str(series.dtype),
                "rows": total,
                "non_null": int(total - n_missing),
                "n_missing": n_missing,
                "pct_missing": round(100 * n_missing / total, 4) if total else 0.0,
                "n_unique": int(non_null.nunique()),
                "sample_values": " | ".join(samples),
            }
        )
    return pd.DataFrame(rows)


def missing_values_table(frame: pd.DataFrame, table_name: str) -> pd.DataFrame:
    """Missing values and their share of the table, most missing first."""
    total = len(frame)
    n_missing = frame.isna().sum()
    result = pd.DataFrame(
        {
            "table": table_name,
            "column": n_missing.index,
            "n_missing": n_missing.to_numpy(dtype="int64"),
        }
    )
    result["pct_missing"] = (100 * result["n_missing"] / total).round(4)
    return (
        result[result["n_missing"] > 0]
        .sort_values("n_missing", ascending=False, ignore_index=True)
    )


def duplicate_rows_table(frame: pd.DataFrame, table_name: str) -> pd.DataFrame:
    """Fully duplicated rows (every column equal) and near-duplicates on keys."""
    n_dup = int(frame.duplicated().sum())
    return pd.DataFrame(
        [
            {
                "table": table_name,
                "rows": len(frame),
                "duplicate_rows_all_columns": n_dup,
                "pct_duplicate_rows": round(100 * n_dup / len(frame), 4) if len(frame) else 0.0,
            }
        ]
    )


def key_uniqueness(frame: pd.DataFrame, keys: tuple[str, ...] | list[str], table_name: str) -> dict:
    """Validate a declared primary key.

    Returns row counts, how many distinct key tuples exist, and how many rows
    sit on a key that appears more than once.
    """
    keys = list(keys)
    missing_columns = [k for k in keys if k not in frame.columns]
    if missing_columns:
        return {
            "table": table_name,
            "key": ", ".join(keys),
            "status": "COLUMN_MISSING",
            "n_rows": len(frame),
            "n_distinct": None,
            "n_duplicated_keys": None,
            "n_rows_on_duplicate_keys": None,
            "n_null_in_key": None,
        }
    if not keys:
        return {
            "table": table_name,
            "key": "(none declared)",
            "status": "NO_DECLARED_KEY",
            "n_rows": len(frame),
            "n_distinct": None,
            "n_duplicated_keys": None,
            "n_rows_on_duplicate_keys": None,
            "n_null_in_key": None,
        }

    null_in_key = int(frame[keys].isna().any(axis=1).sum())
    key_frame = frame[keys].astype("str")
    counts = key_frame.value_counts(dropna=False)
    duplicated_keys = counts[counts > 1]
    n_distinct = int(len(counts))

    return {
        "table": table_name,
        "key": ", ".join(keys),
        "status": "UNIQUE" if len(duplicated_keys) == 0 else "NOT_UNIQUE",
        "n_rows": len(frame),
        "n_distinct": n_distinct,
        "n_duplicated_keys": int(len(duplicated_keys)),
        "n_rows_on_duplicate_keys": int(duplicated_keys.sum()),
        "n_null_in_key": null_in_key,
    }


def key_uniqueness_table(
    tables: dict[str, pd.DataFrame], specs: dict | None = None
) -> pd.DataFrame:
    """Run :func:`key_uniqueness` for every table's declared key."""
    specs = specs or RAW_TABLES
    rows = [
        key_uniqueness(tables[name], spec.primary_key, name)
        for name, spec in specs.items()
        if name in tables
    ]
    return pd.DataFrame(rows)


def referential_integrity(
    child: pd.DataFrame,
    child_column: str,
    parent_keys: set,
    child_label: str,
    parent_label: str,
) -> dict:
    """How many child rows point at a parent row that does not exist.

    Duplicated values in the child column are expected (a customer can place
    many orders); the ratio is therefore reported per *distinct* value, which
    is the number a join can actually lose.
    """
    values = child[child_column].dropna().astype("str")
    distinct = set(values.unique())
    orphans = distinct - {str(k) for k in parent_keys}
    return {
        "relationship": f"{child_label}.{child_column} -> {parent_label}",
        "n_child_rows": int(len(child)),
        "n_distinct_child_values": int(len(distinct)),
        "n_matched_distinct": int(len(distinct) - len(orphans)),
        "n_orphan_distinct": int(len(orphans)),
        "pct_orphan_rows": round(100 * values.isin(orphans).sum() / len(values), 4)
        if len(values)
        else 0.0,
        "example_orphans": " | ".join(sorted(orphans)[:3]),
    }


def value_counts_table(series: pd.Series, value_name: str, top: int | None = None) -> pd.DataFrame:
    """Frequency table with counts and shares that sum to exactly 100%."""
    counts = series.value_counts(dropna=False)
    if top is not None:
        counts = counts.head(top)
    total = int(counts.sum())
    return pd.DataFrame(
        {
            value_name: counts.index.astype("str"),
            "n": counts.to_numpy(dtype="int64"),
            "pct": (100 * counts.to_numpy() / total).round(3) if total else 0.0,
        }
    )


def numeric_range_check(
    frame: pd.DataFrame, columns: list[str], table_name: str
) -> pd.DataFrame:
    """Min / median / max plus count of negative and zero values per column."""
    rows = []
    for column in columns:
        if column not in frame.columns:
            continue
        series = pd.to_numeric(frame[column], errors="coerce")
        rows.append(
            {
                "table": table_name,
                "column": column,
                "n_valid": int(series.notna().sum()),
                "min": float(series.min()) if series.notna().any() else None,
                "median": float(series.median()) if series.notna().any() else None,
                "mean": round(float(series.mean()), 4) if series.notna().any() else None,
                "max": float(series.max()) if series.notna().any() else None,
                "n_negative": int((series < 0).sum()),
                "n_zero": int((series == 0).sum()),
            }
        )
    return pd.DataFrame(rows)


def datetime_parse_report(
    frame: pd.DataFrame, columns: list[str], table_name: str
) -> pd.DataFrame:
    """How many values survive conversion to ``datetime64`` and their range."""
    rows = []
    for column in columns:
        if column not in frame.columns:
            continue
        parsed = pd.to_datetime(frame[column], errors="coerce", format="mixed")
        n_valid = int(parsed.notna().sum())
        rows.append(
            {
                "table": table_name,
                "column": column,
                "n_rows": int(len(frame)),
                "n_parsed": n_valid,
                "n_unparseable": int(frame[column].notna().sum()) - n_valid,
                "n_missing": int(frame[column].isna().sum()),
                "min": parsed.min(),
                "max": parsed.max(),
            }
        )
    return pd.DataFrame(rows)


def group_size_distribution(
    frame: pd.DataFrame, group_column: str, value_column: str, table_name: str
) -> dict:
    """Describe how many rows each group holds (used to justify sample limits)."""
    sizes = frame.groupby(group_column)[value_column].size()
    return {
        "table": table_name,
        "group_column": group_column,
        "n_groups": int(len(sizes)),
        "min": int(sizes.min()) if len(sizes) else 0,
        "median": float(sizes.median()) if len(sizes) else 0.0,
        "mean": round(float(sizes.mean()), 3) if len(sizes) else 0.0,
        "p90": float(sizes.quantile(0.9)) if len(sizes) else 0.0,
        "max": int(sizes.max()) if len(sizes) else 0,
        "n_groups_size_1": int((sizes == 1).sum()),
    }
