#!/usr/bin/env bash
# fetch_datasets.sh — Phase 15a real-dataset downloader.
#
# Downloads the pinned DOLCE-DUL 4.1 + OEWN 2024 datasets into
# `data/datasets/`. FrameNet 1.7 is NOT downloaded — Berkeley
# requires a click-through license that this script cannot accept on
# the user's behalf. See `docs/knowledge-sources/framenet.md` for the
# manual download instruction.
#
# Phase 15a PB-3-i (Round 3) — synthetic fixtures live in
# `tests/phase_15a/fixtures/` for the CI test surface; this script
# is opt-in for real-dataset integration testing (Phase 26's natural
# beat) and for production admin install.
#
# Usage:
#   scripts/fetch_datasets.sh           # fetch DOLCE + OEWN
#   scripts/fetch_datasets.sh dolce     # fetch only DOLCE
#   scripts/fetch_datasets.sh oewn      # fetch only OEWN
#
# Idempotent: skips download if the target file already exists.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${REPO_ROOT}/data/datasets"

DOLCE_URL="http://www.ontologydesignpatterns.org/ont/dul/DUL.owl"
DOLCE_PATH="${DATA_DIR}/dolce-dul-4.1.owl"
DOLCE_VERSION="4.1"

OEWN_URL="https://en-word.net/static/english-wordnet-2024.xml.gz"
OEWN_PATH="${DATA_DIR}/oewn-2024.xml"
OEWN_VERSION="2024"

mkdir -p "${DATA_DIR}"

fetch_dolce() {
    if [[ -f "${DOLCE_PATH}" ]]; then
        echo "[dolce] already present at ${DOLCE_PATH} (skip)"
        return 0
    fi
    echo "[dolce] downloading DOLCE-DUL ${DOLCE_VERSION} from ${DOLCE_URL}"
    curl -fSL --retry 3 -o "${DOLCE_PATH}" "${DOLCE_URL}"
    echo "[dolce] saved to ${DOLCE_PATH}"
}

fetch_oewn() {
    if [[ -f "${OEWN_PATH}" ]]; then
        echo "[oewn] already present at ${OEWN_PATH} (skip)"
        return 0
    fi
    local tmp_gz="${OEWN_PATH}.gz"
    echo "[oewn] downloading OEWN ${OEWN_VERSION} from ${OEWN_URL}"
    curl -fSL --retry 3 -o "${tmp_gz}" "${OEWN_URL}"
    echo "[oewn] decompressing"
    gunzip -f "${tmp_gz}"
    echo "[oewn] saved to ${OEWN_PATH}"
}

framenet_note() {
    cat <<'EOF'

[framenet] NOT downloaded.

Berkeley FrameNet 1.7 requires an explicit click-through license
agreement. Visit:

    https://framenet.icsi.berkeley.edu/fndrupal/framenet_request_data

Accept the license, download fndata-1.7.zip, and place its
extracted contents at:

    data/datasets/framenet-1.7/

The FrameNetImporter auto-detects this directory layout via
`framenet_dir.is_dir()` and reads `frame/*.xml` + `frRelation.xml`.

EOF
}

TARGET="${1:-all}"
case "${TARGET}" in
    dolce)    fetch_dolce ;;
    oewn)     fetch_oewn ;;
    framenet) framenet_note ;;
    all)      fetch_dolce; fetch_oewn; framenet_note ;;
    *)
        echo "Unknown target: ${TARGET}" >&2
        echo "Usage: $0 [dolce|oewn|framenet|all]" >&2
        exit 1
        ;;
esac

echo "Done. Pinned versions: DOLCE-DUL ${DOLCE_VERSION} / OEWN ${OEWN_VERSION} / FrameNet 1.7 (manual)."
