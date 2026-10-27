"""Reading the raw Olist CSVs, with a transparent parquet cache.

The loader is deliberately split in two stages:

``load_raw_tables``
    Reads the CSV files *as they are*.  Timestamp columns stay as strings so
    that the data-quality stage can inspect the raw dtypes and the number of
    unparseable values.  The loaded frames are cached as parquet inside
    ``data/interim/`` because the geolocation file alone holds one million
    rows and re-parsing it for every notebook would make the pipeline painful.

Cache validity is decided from the source file's size and modification time,
recorded in a sidecar JSON file.  Replacing a CSV therefore invalidates the
cache automatically and no stale number can ever leak into the analysis.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from .config import DATA_INTERIM_DIR, RAW_TABLES, TableSpec

_CACHE_DIR = DATA_INTERIM_DIR / "cache"
_FINGERPRINT_FILE = _CACHE_DIR / "_fingerprints.json"


def sha256_short(path: Path, length: int = 16) -> str:
    """First ``length`` hex characters of a file's SHA-256 digest."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()[:length]


def file_inventory() -> pd.DataFrame:
    """Physical inventory of every expected raw file (no parsing involved)."""
    rows = []
    for spec in RAW_TABLES.values():
        exists = spec.path.exists()
        stat = spec.path.stat() if exists else None
        rows.append(
            {
                "table": spec.name,
                "filename": spec.filename,
                "exists": exists,
                "size_bytes": stat.st_size if stat else 0,
                "size_mb": round(stat.st_size / 1024**2, 2) if stat else 0.0,
                "sha256_16": sha256_short(spec.path) if exists else "",
            }
        )
    return pd.DataFrame(rows)


def _source_fingerprint(spec: TableSpec) -> dict[str, int]:
    stat = spec.path.stat()
    return {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns}


def _read_fingerprints() -> dict[str, dict[str, int]]:
    if _FINGERPRINT_FILE.exists():
        try:
            return json.loads(_FINGERPRINT_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def _write_fingerprints(data: dict[str, dict[str, int]]) -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _FINGERPRINT_FILE.write_text(
        json.dumps(data, indent=2, sort_keys=True), encoding="utf-8"
    )


def _cache_path(spec: TableSpec, stage: str) -> Path:
    return _CACHE_DIR / f"{stage}__{spec.name}.parquet"


def _cache_is_valid(spec: TableSpec, stage: str, fingerprints: dict) -> bool:
    path = _cache_path(spec, stage)
    if not path.exists():
        return False
    stored = fingerprints.get(f"{stage}:{spec.name}")
    return stored == _source_fingerprint(spec)


def load_raw_tables(
    names: list[str] | None = None,
    *,
    use_cache: bool = True,
    force_reload: bool = False,
) -> dict[str, pd.DataFrame]:
    """Load raw tables, using the parquet cache when the CSV is unchanged.

    Parameters
    ----------
    names:
        Subset of :data:`~olist_analysis.config.RAW_TABLES` keys to load.
        ``None`` loads every table.
    """
    selected = list(RAW_TABLES) if names is None else names
    fingerprints = _read_fingerprints()
    tables: dict[str, pd.DataFrame] = {}
    dirty = False

    for name in selected:
        spec = RAW_TABLES[name]
        if not spec.path.exists():
            raise FileNotFoundError(
                f"Raw dataset missing: {spec.path}. "
                "See data/README.md for download instructions."
            )

        if use_cache and not force_reload and _cache_is_valid(spec, "raw", fingerprints):
            tables[name] = pd.read_parquet(_cache_path(spec, "raw"))
            continue

        frame = pd.read_csv(spec.path, encoding="utf-8")
        tables[name] = frame

        if use_cache:
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)
            frame.to_parquet(_cache_path(spec, "raw"), index=False)
            fingerprints[f"raw:{name}"] = _source_fingerprint(spec)
            dirty = True

    if dirty:
        _write_fingerprints(fingerprints)

    return tables


def load_raw_table(name: str, **kwargs) -> pd.DataFrame:
    """Convenience wrapper for a single table."""
    return load_raw_tables([name], **kwargs)[name]


def table_shapes(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Row / column count per table, in the canonical order of the brief."""
    rows = []
    for name in RAW_TABLES:
        if name in tables:
            frame = tables[name]
            rows.append(
                {"table": name, "rows": int(frame.shape[0]), "columns": int(frame.shape[1])}
            )
    return pd.DataFrame(rows)


def clear_cache() -> None:
    """Delete every cached parquet file and its fingerprint sidecar."""
    if _CACHE_DIR.exists():
        for path in _CACHE_DIR.glob("*.parquet"):
            path.unlink()
    if _FINGERPRINT_FILE.exists():
        _FINGERPRINT_FILE.unlink()
