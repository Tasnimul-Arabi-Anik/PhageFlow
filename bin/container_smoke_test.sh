#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ROOT="$(cd "${ROOT}/.." && pwd)"
IMAGE="${PHAGEFLOW_CONTAINER_IMAGE:-phageflow:smoke}"
if [[ -n "${PHAGEFLOW_CONTAINER_OUTDIR:-}" ]]; then
  OUTDIR="${PHAGEFLOW_CONTAINER_OUTDIR}"
else
  OUTDIR="$(mktemp -d /tmp/phageflow_container_smoke_results.XXXXXX)"
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker not found on PATH." >&2
  exit 127
fi

docker build -t "${IMAGE}" -f "${ROOT}/containers/Dockerfile" "${ROOT}"
if [[ -n "${PHAGEFLOW_CONTAINER_OUTDIR:-}" ]]; then
  rm -rf "${OUTDIR}"
fi
mkdir -p "${OUTDIR}"

docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -v "${PROJECT_ROOT}:/work" \
  -v "${OUTDIR}:/out" \
  -w /work \
  "${IMAGE}" \
  nextflow run phageflow/main.nf \
    --input phageflow/assets/test_data/toy_phage_a.fasta \
    --pangenome_method none \
    --outdir /out/results

python3 "${ROOT}/bin/validate_phageflow_run.py" --outdir "${OUTDIR}/results"
python3 "${ROOT}/bin/summarize_run.py" --outdir "${OUTDIR}/results" --output "${OUTDIR}/artifact_summary.json"
python3 "${ROOT}/bin/package_run.py" --outdir "${OUTDIR}/results" --output "${OUTDIR}/phageflow_container_smoke_package.tar.gz" --force

echo "Container smoke test passed: ${OUTDIR}"
