#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

python scripts/run_router_phase10_system.py \
  --enforce-gate \
  --out-dir outputs/router_phase10_system_v1 \
  --report-md reports/router_phase10_system_v1.md

