"""Build the deliverable ZIP archive.

    python scripts/build_deliverables.py

The archive contains the source, the executed notebooks, the reports and the
documentation.  Raw CSV data, caches, virtual environments and anything that
could carry a secret are explicitly excluded - see ``deliverables/README.md``
for the inclusion policy and ``data/README.md`` for how a reviewer obtains the
raw data.
"""

from __future__ import annotations

import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DELIVERABLES_DIR = PROJECT_ROOT / "deliverables"
ARCHIVE = DELIVERABLES_DIR / "olist-pro-deliverables.zip"

INCLUDE_DIRECTORIES = [
    "src",
    "scripts",
    "tests",
    "notebooks",
    "docs",
    "reports/figures",
    "reports/tables",
]
INCLUDE_FILES = [
    "README.md",
    "requirements.txt",
    "pyproject.toml",
    ".gitignore",
    ".gitattributes",
    "data/README.md",
    "reports/executive_report.md",
    "reports/executive_report.pdf",
    "reports/metrics.json",
    "deliverables/README.md",
]

EXCLUDED_PATTERNS = [
    ".venv",
    "venv",
    "__pycache__",
    ".ipynb_checkpoints",
    ".git/",
    ".pytest_cache",
    ".pyc",
    ".tmp",
    ".log",
]
EXCLUDED_SUFFIXES = [".csv"]  # raw data never travels inside the archive


def should_skip(path: Path) -> bool:
    text = path.as_posix()
    if any(pattern in text for pattern in EXCLUDED_PATTERNS):
        return True
    if path.suffix == ".pyc":
        return True
    # ``data/raw`` is the only place large CSVs live; keep every other CSV out too,
    # because the tables are already reproducible from the pipeline.
    if path.suffix in EXCLUDED_SUFFIXES and "data/" in text:
        return True
    if any(part.startswith(".") and part not in {".gitignore", ".gitattributes"} for part in path.parts):
        return True
    return False


def collect_files() -> list[Path]:
    files: list[Path] = []
    for relative in INCLUDE_DIRECTORIES:
        directory = PROJECT_ROOT / relative
        if not directory.exists():
            print(f"warning: missing directory {relative}")
            continue
        for path in sorted(directory.rglob("*")):
            if path.is_file() and not should_skip(path.relative_to(PROJECT_ROOT)):
                files.append(path)
    for relative in INCLUDE_FILES:
        path = PROJECT_ROOT / relative
        if path.exists() and not should_skip(Path(relative)):
            files.append(path)
        else:
            print(f"warning: missing file {relative}")
    return files


def build_archive(archive: Path = ARCHIVE) -> tuple[Path, int, int]:
    DELIVERABLES_DIR.mkdir(parents=True, exist_ok=True)
    files = collect_files()

    manifest_lines = [
        "olist-pro deliverables archive",
        f"built (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"files: {len(files)}",
        "",
        "Contents:",
    ]
    for path in files:
        manifest_lines.append(f"  {path.relative_to(PROJECT_ROOT).as_posix()}")

    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in files:
            zf.write(path, path.relative_to(PROJECT_ROOT).as_posix())
        zf.writestr("MANIFEST.txt", "\n".join(manifest_lines) + "\n")

    size_mb = archive.stat().st_size / 1024**2
    return archive, len(files), int(size_mb * 1024)


def main() -> int:
    archive, count, size_kb = build_archive()
    print(f"archive : {archive}")
    print(f"files   : {count}")
    print(f"size    : {size_kb / 1024:.2f} MB")

    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
        # only *raw* data must stay out; the analysis tables in reports/tables
        # are part of the deliverable
        bad = [
            name
            for name in names
            if (name.endswith(".csv") and name.startswith("data/"))
            or ".venv" in name
            or "__pycache__" in name
        ]
        print(f"entries : {len(names)}")
        if bad:
            print("ERROR: archive contains excluded content:")
            for name in bad[:10]:
                print("  -", name)
            return 1
        print("policy  : OK - no raw CSV, no virtualenv, no cache")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
