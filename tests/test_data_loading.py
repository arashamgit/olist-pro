"""Tests for the loading layer: file inventory, hashing, cache behaviour."""

from __future__ import annotations

import pandas as pd

from olist_analysis.config import RAW_TABLES
from olist_analysis.data_loader import (
    file_inventory,
    load_raw_table,
    load_raw_tables,
    sha256_short,
    table_shapes,
)


def test_sha256_short_length_and_stability(tmp_path):
    path = tmp_path / "sample.csv"
    path.write_text("a,b\n1,2\n", encoding="utf-8")
    first = sha256_short(path)
    second = sha256_short(path)
    assert len(first) == 16
    assert first == second
    assert first == sha256_short(path, length=16)


def test_file_inventory_covers_every_expected_table():
    inventory = file_inventory()
    assert set(inventory["table"]) == set(RAW_TABLES)
    assert inventory["size_bytes"].gt(0).all()
    # the raw size reported by the course brief is ~120 MB
    assert inventory["size_mb"].sum() > 100


def test_file_inventory_reports_missing_files_honestly(monkeypatch, tmp_path):
    from olist_analysis import data_loader

    missing_spec = RAW_TABLES["orders"]
    monkeypatch.setattr(
        type(missing_spec), "path", property(lambda self: tmp_path / "does_not_exist.csv")
    )
    inventory = data_loader.file_inventory()
    assert not inventory["exists"].all()
    assert (inventory.loc[~inventory["exists"], "size_bytes"] == 0).all()


def test_table_shapes_reads_row_and_column_counts():
    tables = {"orders": pd.DataFrame({"a": [1, 2, 3]}), "customers": pd.DataFrame({"b": [1]})}
    shapes = table_shapes(tables)
    rows = dict(zip(shapes["table"], shapes["rows"]))
    assert rows["orders"] == 3
    assert rows["customers"] == 1


def test_raw_loading_is_consistent_with_the_files_on_disk():
    tables = load_raw_tables(["orders", "customers"])
    assert set(tables) == {"orders", "customers"}
    assert len(tables["orders"]) == len(tables["customers"])
    # timestamps must still be text at the raw stage
    assert tables["orders"]["order_purchase_timestamp"].dtype == "str"


def test_single_table_loader_matches_bulk_loader():
    bulk = load_raw_tables(["sellers"])["sellers"]
    single = load_raw_table("sellers")
    assert len(bulk) == len(single)
    assert list(bulk.columns) == list(single.columns)
