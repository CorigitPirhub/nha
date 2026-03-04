#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

bash scripts/run_router_phase7_all.sh
bash scripts/run_router_phase8_strict_all.sh
bash scripts/run_router_phase9_bench_all.sh
bash scripts/run_router_phase10_system_all.sh
bash scripts/run_router_phase11_theory_all.sh
bash scripts/run_router_phase12_realworld_all.sh
bash scripts/run_router_phase13_sota_all.sh
bash scripts/run_router_phase14_stress_all.sh
python scripts/run_router_phase15_camera_ready.py --enforce-gate
