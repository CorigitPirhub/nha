#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

# Main paper pipeline (frozen protocol + 5-seed reporting).
bash scripts/run_router_phase7_all.sh
bash scripts/run_router_phase8_strict_all.sh
bash scripts/run_router_phase9_bench_all.sh
bash scripts/run_router_phase10_system_all.sh
bash scripts/run_router_phase11_theory_all.sh
bash scripts/run_router_phase12_realworld_all.sh
bash scripts/run_router_phase13_sota_all.sh
bash scripts/run_router_phase14_stress_all.sh

# Step 1 (Phase16): related-work baselines.
python scripts/run_router_phase16_related_baselines.py --enforce-gate

# Step 2 (Phase17): offline policy == system policy (rule vs policy closed-loop).
python scripts/run_router_phase10_system.py --enforce-gate --router-mode rule --out-dir outputs/router_phase17_policy_alignment_v1/rule/phase10 --report-md outputs/router_phase17_policy_alignment_v1/rule/phase10/report.md
python scripts/run_router_phase10_system.py --enforce-gate --router-mode policy --out-dir outputs/router_phase17_policy_alignment_v1/policy/phase10 --report-md outputs/router_phase17_policy_alignment_v1/policy/phase10/report.md
python scripts/run_router_phase12_realworld.py --enforce-gate --router-mode rule --out-dir outputs/router_phase17_policy_alignment_v1/rule/phase12 --report-md outputs/router_phase17_policy_alignment_v1/rule/phase12/report.md
python scripts/run_router_phase12_realworld.py --enforce-gate --router-mode policy --out-dir outputs/router_phase17_policy_alignment_v1/policy/phase12 --report-md outputs/router_phase17_policy_alignment_v1/policy/phase12/report.md
python scripts/run_router_phase14_stress.py --enforce-gate --router-mode rule --out-dir outputs/router_phase17_policy_alignment_v1/rule/phase14 --report-md outputs/router_phase17_policy_alignment_v1/rule/phase14/report.md
python scripts/run_router_phase14_stress.py --enforce-gate --router-mode policy --out-dir outputs/router_phase17_policy_alignment_v1/policy/phase14 --report-md outputs/router_phase17_policy_alignment_v1/policy/phase14/report.md
python scripts/run_router_phase17_policy_alignment.py --enforce-gate

# Step 4 (Phase19): secondary metrics.
python scripts/run_router_phase19_metrics_extension.py --enforce-gate

# Phase20: build camera-ready v2 bundle + final_v2 manifest.
python scripts/run_router_phase20_camera_ready_v2.py --enforce-gate
