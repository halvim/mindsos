#!/usr/bin/env bash
# Regenerate locked requirements*.txt files using pip-compile inside the pinned
# Python image (matches the digest from mindsos_cli/manifest.toml).
#
# WHEN TO RUN
#   - Once on the Linux box during Phase 00 setup (after `git pull` of phase-00).
#   - Whenever requirements.in or requirements-test.in changes.
#
# WHAT IT DOES
#   1. Pulls the pinned Python image (idempotent after first run).
#   2. Runs `pip-compile --generate-hashes` inside that image to produce
#      requirements.txt and requirements-test.txt with bit-identical hashes.
#   3. Prints the sha256 of requirements.txt; you paste it into
#      mindsos_cli/manifest.toml under [lockfile] requirements_txt_sha256.
#
# WHAT TO COMMIT AFTER RUNNING
#   - requirements.txt
#   - requirements-test.txt
#   - mindsos_cli/manifest.toml (with the updated sha256)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_IMAGE="python@sha256:afc139a0a640942491ec481ad8dda10f2c5b753f5c969393b12480155fe15a63"

cd "$REPO_ROOT"

run_pip_compile() {
    local in_file="$1"
    local out_file="$2"
    docker run --rm \
        --user "$(id -u):$(id -g)" \
        -e HOME=/tmp \
        -v "$REPO_ROOT:/work" \
        -w /work \
        "$PYTHON_IMAGE" \
        bash -c "
            set -euo pipefail
            pip install --quiet --user --no-warn-script-location pip-tools
            export PATH=/tmp/.local/bin:\$PATH
            pip-compile --quiet --generate-hashes \
                --output-file '$out_file' \
                '$in_file'
        "
}

echo "==> Pulling pinned Python image (idempotent)..."
docker pull "$PYTHON_IMAGE"

echo "==> Generating requirements.txt..."
run_pip_compile requirements.in requirements.txt

echo "==> Generating requirements-test.txt..."
run_pip_compile requirements-test.in requirements-test.txt

REQ_HASH=$(sha256sum requirements.txt | awk '{print $1}')

echo ""
echo "==> Lockfiles regenerated."
echo ""
echo "    requirements.txt sha256: $REQ_HASH"
echo ""
echo "Next steps:"
echo "  1. Open mindsos_cli/manifest.toml."
echo "  2. Replace the [lockfile] requirements_txt_sha256 value with:"
echo "       \"$REQ_HASH\""
echo "  3. git add requirements.txt requirements-test.txt mindsos_cli/manifest.toml"
echo "  4. git commit -m \"Phase 00: lock requirements\""
echo ""
