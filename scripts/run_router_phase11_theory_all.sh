#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

python scripts/run_router_phase11_theory.py \
  --enforce-gate \
  --out-dir outputs/router_phase11_theory_v1 \
  --report-md reports/router_phase11_theory_v1.md

