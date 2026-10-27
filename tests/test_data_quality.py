"""Tests for the data-quality probes, on controlled synthetic frames."""

from __future__ import annotations

import pandas as pd
import pytest

from olist_analysis.data_quality import (
    column_profile,
    datetime_parse_report,
    duplicate_rows_table,
    key_uniqueness,
    missing_values_table,
    numeric_range_check,
    referential_integrity,
    value_counts_table,
)


@pytest.fixture
def frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": ["a", "b", "b", "c"],
            "value": [1.0, 2.0, 2.0, -5.0],
            "text": ["x", None, None, "y"],
        }
    )


def test_column_profile_counts_missing_and_unique(frame):
    profile = column_profile(frame, "demo").set_index("column")
    assert profile.loc["text", "n_missing"] == 2
    assert profile.loc["text", "pct_missing"] == 50.0
    assert profile.loc["id", "n_unique"] == 3
    assert profile.loc["value", "rows"] == 4


def test_missing_values_table_only_lists_incomplete_columns(frame):
    missing = missing_values_table(frame, "demo")
    assert list(missing["column"]) == ["text"]
    assert missing.iloc[0]["n_missing"] == 2


def test_duplicate_rows_table(frame):
    duplicates = duplicate_rows_table(frame, "demo")
    assert duplicates.iloc[0]["duplicate_rows_all_columns"] == 1


def test_key_uniqueness_detects_duplicates_and_nulls():
    unique = pd.DataFrame({"k": ["1", "2", "3"]})
    assert key_uniqueness(unique, ("k",), "t")["status"] == "UNIQUE"

    duplicated = pd.DataFrame({"k": ["1", "1", "2"]})
    result = key_uniqueness(duplicated, ("k",), "t")
    assert result["status"] == "NOT_UNIQUE"
    assert result["n_duplicated_keys"] == 1
    assert result["n_rows_on_duplicate_keys"] == 2

    with_null = pd.DataFrame({"k": ["1", None]})
    result = key_uniqueness(with_null, ("k",), "t")
    assert result["n_null_in_key"] == 1

    result = key_uniqueness(unique, ("missing",), "t")
    assert result["status"] == "COLUMN_MISSING"


def test_composite_key_uniqueness():
    frame = pd.DataFrame({"a": ["1", "1", "2"], "b": ["1", "2", "1"]})
    assert key_uniqueness(frame, ("a", "b"), "t")["status"] == "UNIQUE"
    assert key_uniqueness(frame, ("a",), "t")["status"] == "NOT_UNIQUE"


def test_referential_integrity_counts_orphans_per_distinct_value():
    child = pd.DataFrame({"order_id": ["o1", "o1", "o2", "o9"]})
    result = referential_integrity(child, "order_id", {"o1", "o2"}, "child", "parent")
    assert result["n_distinct_child_values"] == 3
    assert result["n_orphan_distinct"] == 1
    assert result["pct_orphan_rows"] == 25.0
    assert result["example_orphans"] == "o9"


def test_value_counts_percentages_sum_to_one_hundred():
    series = pd.Series(["a", "a", "b", "c"])
    table = value_counts_table(series, "kind")
    assert table["n"].sum() == 4
    assert table["pct"].sum() == pytest.approx(100.0)


def test_numeric_range_check_flags_negative_and_zero():
    frame = pd.DataFrame({"x": [0.0, -1.0, 5.0]})
    result = numeric_range_check(frame, ["x"], "t").iloc[0]
    assert result["n_negative"] == 1
    assert result["n_zero"] == 1
    assert result["min"] == -1.0
    assert result["max"] == 5.0


def test_datetime_parse_report_counts_unparseable_values():
    frame = pd.DataFrame({"ts": ["2017-01-01 10:00:00", "not-a-date", None]})
    result = datetime_parse_report(frame, ["ts"], "t").iloc[0]
    assert result["n_parsed"] == 1
    assert result["n_unparseable"] == 1
    assert result["n_missing"] == 1
