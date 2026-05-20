#!/usr/bin/env python3
"""fetch_datasets.py — Phase 15a real-dataset downloader (Python fallback).

Functional parity with ``scripts/fetch_datasets.sh`` for environments
without bash (Windows + restricted CI). Downloads pinned DOLCE-DUL 4.1
and OEWN 2024 into ``data/datasets/``; FrameNet requires manual
download per Berkeley click-through (see
``docs/knowledge-sources/framenet.md``).

Phase 15a PB-3-i (Round 3) lock: synthetic fixtures cover the test
surface; this script is opt-in for real-dataset integration testing
(Phase 26's natural beat).
"""

from __future__ import annotations

import argparse
import gzip
import shutil
import sys
import urllib.request
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data" / "datasets"

DOLCE_URL = "http://www.ontologydesignpatterns.org/ont/dul/DUL.owl"
DOLCE_PATH = DATA_DIR / "dolce-dul-4.1.owl"
DOLCE_VERSION = "4.1"

OEWN_URL = "https://en-word.net/static/english-wordnet-2024.xml.gz"
OEWN_PATH = DATA_DIR / "oewn-2024.xml"
OEWN_VERSION = "2024"


def _download(url: str, dest: Path) -> None:
    print(f"  downloading {url}", flush=True)
    with urllib.request.urlopen(url) as response, dest.open("wb") as out:
        shutil.copyfileobj(response, out)


def fetch_dolce() -> None:
    if DOLCE_PATH.exists():
        print(f"[dolce] already present at {DOLCE_PATH} (skip)")
        return
    print(f"[dolce] downloading DOLCE-DUL {DOLCE_VERSION}")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _download(DOLCE_URL, DOLCE_PATH)
    print(f"[dolce] saved to {DOLCE_PATH}")


def fetch_oewn() -> None:
    if OEWN_PATH.exists():
        print(f"[oewn] already present at {OEWN_PATH} (skip)")
        return
    tmp_gz = OEWN_PATH.with_suffix(OEWN_PATH.suffix + ".gz")
    print(f"[oewn] downloading OEWN {OEWN_VERSION}")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _download(OEWN_URL, tmp_gz)
    print("[oewn] decompressing")
    with gzip.open(tmp_gz, "rb") as gz_in, OEWN_PATH.open("wb") as out:
        shutil.copyfileobj(gz_in, out)
    tmp_gz.unlink()
    print(f"[oewn] saved to {OEWN_PATH}")


def framenet_note() -> None:
    print(
        "\n[framenet] NOT downloaded.\n"
        "\n"
        "Berkeley FrameNet 1.7 requires an explicit click-through license\n"
        "agreement. Visit:\n"
        "\n"
        "    https://framenet.icsi.berkeley.edu/fndrupal/framenet_request_data\n"
        "\n"
        "Accept the license, download fndata-1.7.zip, and place its\n"
        "extracted contents at:\n"
        "\n"
        "    data/datasets/framenet-1.7/\n"
        "\n"
        "The FrameNetImporter auto-detects this directory layout via\n"
        "`framenet_dir.is_dir()` and reads `frame/*.xml` + `frRelation.xml`.\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Phase 15a real-dataset downloader.",
    )
    parser.add_argument(
        "target",
        nargs="?",
        default="all",
        choices=["dolce", "oewn", "framenet", "all"],
        help="Which dataset to fetch. Default: all.",
    )
    args = parser.parse_args(argv)

    if args.target in ("dolce", "all"):
        fetch_dolce()
    if args.target in ("oewn", "all"):
        fetch_oewn()
    if args.target in ("framenet", "all"):
        framenet_note()

    print(
        f"\nDone. Pinned versions: DOLCE-DUL {DOLCE_VERSION} / "
        f"OEWN {OEWN_VERSION} / FrameNet 1.7 (manual)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
