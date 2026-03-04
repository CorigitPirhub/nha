#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

python scripts/run_router_phase15_camera_ready.py \
  --enforce-gate \
  --artifact-dir artifacts/router_camera_ready_v1 \
  --report-md reports/router_phase15_camera_ready_v1.md \
  --checklist-md paper/final_submission_checklist.md
