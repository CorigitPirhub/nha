from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import stat
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ClaimItem:
    claim_id: str
    claim_text: str
    metric_name: str
    metric_value: str
    target: str
    passed: bool
    evidence_paths: list[Path]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase-26 camera-ready packaging (V3) + final_v3 manifest.")
    p.add_argument("--artifact-dir", type=Path, default=Path("artifacts/router_camera_ready_v3"))
    p.add_argument("--final-dir", type=Path, default=Path("outputs/final_v3"))
    p.add_argument("--report-md", type=Path, default=Path("reports/router_phase26_camera_ready_v3.md"))
    p.add_argument("--checklist-md", type=Path, default=Path("paper/final_submission_checklist.md"))
    p.add_argument("--runtime-target-hours", type=float, default=48.0)
    p.add_argument("--enforce-gate", action="store_true", default=True)
    return p.parse_args()


def _load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _ensure_exec(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _copytree_overwrite(src: Path, dst: Path) -> None:
    if not src.exists():
        raise FileNotFoundError(src)
    if src.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return
    shutil.copytree(src, dst, dirs_exist_ok=True)


def _write_repro_bundle(artifact_dir: Path) -> dict[str, Path]:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir = artifact_dir / "evidence"
    if evidence_dir.exists():
        shutil.rmtree(evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    dockerfile = artifact_dir / "Dockerfile"
    dockerfile.write_text(
        "\n".join(
            [
                "FROM python:3.11-slim",
                "WORKDIR /workspace",
                "COPY requirements.txt /workspace/requirements.txt",
                "RUN pip install --no-cache-dir -r /workspace/requirements.txt",
                "COPY . /workspace",
                "ENV PYTHONUNBUFFERED=1",
                'CMD ["bash", "artifacts/router_camera_ready_v3/reproduce_main_tables_figures.sh"]',
                "",
            ]
        ),
        encoding="utf-8",
    )

    req_lock = artifact_dir / "requirements.lock.txt"
    req_lock.write_text((ROOT / "requirements.txt").read_text(encoding="utf-8"), encoding="utf-8")

    repro_sh = artifact_dir / "reproduce_main_tables_figures.sh"
    repro_sh.write_text(
        """#!/usr/bin/env bash
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

# Step 6 (Phase21): NeurIPS positioning + minimal core method demo.
python scripts/run_router_phase21_minimal_demo.py

# Step 7 (Phase22): CDT/CRC-style direct baselines under frozen protocol.
python scripts/run_router_phase22_direct_baselines.py --enforce-gate

# Step 8 (Phase23): K=3 portfolio router (requires K3 counterfactual tables).
python scripts/run_router_phase23_build_k3_counterfactual_v1.py --split calib --mid-method midnet --out-parquet outputs/router_phase23_portfolio_v1/common/router_counterfactual_calib_k3_midnet.parquet --out-report outputs/router_phase23_portfolio_v1/common/router_counterfactual_calib_k3_midnet_report.json
python scripts/run_router_phase23_build_k3_counterfactual_v1.py --split test --mid-method midnet --out-parquet outputs/router_phase23_portfolio_v1/common/router_counterfactual_test_k3_midnet.parquet --out-report outputs/router_phase23_portfolio_v1/common/router_counterfactual_test_k3_midnet_report.json
python scripts/run_router_phase23_portfolio_v1.py

# Step 9 (Phase24): theory v3 checks.
python scripts/run_router_phase24_theory_v3.py --enforce-gate

# Step 10 (Phase25): generalization across settings.
python scripts/run_router_phase25_generalization_v1.py

# Phase26: build camera-ready v3 bundle + final_v3 manifest.
python scripts/run_router_phase26_camera_ready_v3.py --enforce-gate
""",
        encoding="utf-8",
    )
    _ensure_exec(repro_sh)

    readme = artifact_dir / "README.md"
    readme.write_text(
        """# Router Camera-Ready Repro Bundle (V3)

This bundle extends V2 by adding NeurIPS/ICML method-level contributions (Step6~Step10):
- Phase21: method abstraction + minimal runnable demo
- Phase22: direct baselines (CDT/CRC-style) under the frozen protocol
- Phase23: K>=3 portfolio routing (multi-arm / multi-budget)
- Phase24: theory v3 with empirical inequality checks
- Phase25: cross-setting generalization (>=2 settings)

## One-Command Reproduction
- `bash artifacts/router_camera_ready_v3/reproduce_main_tables_figures.sh`

## Container Reproduction
1. `docker build -t router-camera-ready-v3 -f artifacts/router_camera_ready_v3/Dockerfile .`
2. `docker run --rm -it router-camera-ready-v3`

## Outputs
- Audit JSON: `artifacts/router_camera_ready_v3/audit_summary.json`
- Manifest: `artifacts/router_camera_ready_v3/MANIFEST.sha256`
- Claim matrix: `artifacts/router_camera_ready_v3/claim_to_evidence.csv`
- Final bundle: `outputs/final_v3/manifest.json`
""",
        encoding="utf-8",
    )

    return {
        "evidence_dir": evidence_dir,
        "dockerfile": dockerfile,
        "requirements_lock": req_lock,
        "repro_sh": repro_sh,
        "readme": readme,
    }


def _required_paths_v3() -> list[Path]:
    rels = [
        # Frozen protocol.
        "docs/router_protocol_v1.md",
        # Method + theory (v1 and v3).
        "docs/neurips_method_v1.md",
        "docs/router_theory_v1.md",
        "docs/router_theory_appendix_v1.md",
        "docs/router_theory_v3.md",
        "docs/router_theory_v3_appendix.md",
        # Core module.
        "utils/router_method_core.py",
        # Phase stats (core system track).
        "outputs/router_phase7_v1/stats.json",
        "outputs/router_phase8_strict_v1/stats.json",
        "outputs/router_phase9_bench_v1/stats.json",
        "outputs/router_phase10_system_v1/stats.json",
        "outputs/router_phase11_theory_v1/stats.json",
        "outputs/router_phase12_realworld_v1/stats.json",
        "outputs/router_phase13_sota_v1/stats.json",
        "outputs/router_phase14_stress_v1/stats.json",
        "outputs/router_phase14_stress_v1/stress_profile_summary.csv",
        # Phase reports (core system track).
        "reports/router_phase7_v1.md",
        "reports/router_phase8_strict_v1.md",
        "reports/router_phase9_bench_v1.md",
        "reports/router_phase10_system_v1.md",
        "reports/router_phase11_theory_v1.md",
        "reports/router_phase12_realworld_v1.md",
        "reports/router_phase13_sota_v1.md",
        "reports/router_phase14_stress_v1.md",
        # Step1/2/4.
        "outputs/router_phase16_related_baselines_v1/stats.json",
        "reports/router_phase16_related_baselines_v1.md",
        "paper/tables_router_v5/table_phase16_related_baselines.csv",
        "paper/appendix_related_baselines.md",
        "outputs/router_phase17_policy_alignment_v1/stats.json",
        "reports/router_phase17_policy_alignment_v1.md",
        "paper/tables_router_v5/table_phase17_policy_alignment.csv",
        "paper/figures_router_v5/fig_policy_alignment_p99_latency.svg",
        "paper/figures_router_v5/fig_policy_alignment_p99_latency.png",
        "artifacts/router_policy_v1/policy.json",
        "artifacts/router_policy_v1/POLICY.sha256",
        "outputs/router_phase19_metrics_extension_v1/stats.json",
        "reports/router_phase19_metrics_extension_v1.md",
        "paper/tables_router_v6/table_secondary_metrics.csv",
        "paper/figures_router_v6/fig_secondary_metrics_clearance_delta.svg",
        "paper/figures_router_v6/fig_secondary_metrics_clearance_delta.png",
        "paper/figures_router_v6/fig_secondary_metrics_proxy_validity.svg",
        "paper/figures_router_v6/fig_secondary_metrics_proxy_validity.png",
        # Step6~10 (NeurIPS track).
        "outputs/router_phase21_neurips_positioning_v1/stats.json",
        "reports/router_phase21_neurips_positioning_v1.md",
        "outputs/router_phase22_direct_baselines_v1/stats.json",
        "reports/router_phase22_direct_baselines_v1.md",
        "paper/tables_router_v7/table_phase22_direct_baselines.csv",
        "outputs/router_phase23_midnet_arm_full_tiny_b64_v1/stats.json",
        "reports/router_phase23_midnet_arm_full_tiny_b64_v1.md",
        "outputs/router_phase23_portfolio_v1/stats.json",
        "reports/router_phase23_portfolio_v1.md",
        "paper/tables_router_v7/table_phase23_portfolio.csv",
        "paper/figures_router_v7/fig_portfolio_tradeoff.svg",
        "outputs/router_phase24_theory_v3/stats.json",
        "outputs/router_phase24_theory_v3/seed_checks.csv",
        "outputs/router_phase24_theory_v3/shift_bounds.csv",
        "outputs/router_phase24_theory_v3/probe_monotone.csv",
        "reports/router_phase24_theory_v3.md",
        "outputs/router_phase25_generalization_v1/stats.json",
        "outputs/router_phase25_generalization_v1/settings/mp/stats.json",
        "outputs/router_phase25_generalization_v1/settings/csm/stats.json",
        "reports/router_phase25_generalization_v1.md",
        "paper/figures_router_v7/fig_generalization_mp.svg",
        "paper/figures_router_v7/fig_generalization_csm.svg",
        # Extra claim evidence for P13 table.
        "paper/tables_router_v3/table_phase13_external_sota_summary.csv",
    ]
    return [ROOT / r for r in rels]


def _runtime_estimate_hours(stats: dict[str, dict]) -> float:
    total = 0.0
    for obj in stats.values():
        if "runtime_hours" in obj:
            total += float(obj.get("runtime_hours", 0.0))
            continue
        if "runtime_seconds" in obj:
            total += float(obj.get("runtime_seconds", 0.0)) / 3600.0
            continue
        if "runtime_s" in obj:
            total += float(obj.get("runtime_s", 0.0)) / 3600.0
            continue
    return float(total)


def _build_claims(stats: dict[str, dict]) -> list[ClaimItem]:
    p11 = stats["p11"]
    p12 = stats["p12"]
    p13 = stats["p13"]
    p14 = stats["p14"]
    p16 = stats["p16"]
    p17 = stats["p17"]
    p19 = stats["p19"]
    p21 = stats["p21"]
    p22 = stats["p22"]
    p23 = stats["p23"]
    p24 = stats["p24"]
    p25 = stats["p25"]

    claims: list[ClaimItem] = [
        # Carry-over claims (Phase12/13/14/11).
        ClaimItem(
            claim_id="C01",
            claim_text="P12 双平台回合数达到 500+",
            metric_name="episodes_per_platform_ge_500",
            metric_value=str(p12["gate_check"].get("episodes_per_platform_ge_500")),
            target="True",
            passed=bool(p12["gate_check"].get("episodes_per_platform_ge_500", False)),
            evidence_paths=[ROOT / "outputs/router_phase12_realworld_v1/stats.json"],
        ),
        ClaimItem(
            claim_id="C02",
            claim_text="P12 安全与尾延迟门槛达标",
            metric_name="success/collision/p95/p99 gates",
            metric_value=str(
                {
                    "success": p12["gate_check"].get("success_ge_97pct_each"),
                    "collision": p12["gate_check"].get("catastrophic_collision_zero_each"),
                    "p95": p12["gate_check"].get("p95_latency_le_50ms_each"),
                    "p99": p12["gate_check"].get("p99_latency_le_80ms_each"),
                }
            ),
            target="all True",
            passed=bool(
                p12["gate_check"].get("success_ge_97pct_each", False)
                and p12["gate_check"].get("catastrophic_collision_zero_each", False)
                and p12["gate_check"].get("p95_latency_le_50ms_each", False)
                and p12["gate_check"].get("p99_latency_le_80ms_each", False)
            ),
            evidence_paths=[
                ROOT / "outputs/router_phase12_realworld_v1/stats.json",
                ROOT / "reports/router_phase12_realworld_v1.md",
            ],
        ),
        ClaimItem(
            claim_id="C03",
            claim_text="P13 外部强基线数量 >= 6",
            metric_name="external_strong_baselines",
            metric_value=str(p13["counts"].get("external_strong_baselines")),
            target=">=6",
            passed=bool(int(p13["counts"].get("external_strong_baselines", 0)) >= 6),
            evidence_paths=[
                ROOT / "outputs/router_phase13_sota_v1/stats.json",
                ROOT / "paper/tables_router_v3/table_phase13_external_sota_summary.csv",
            ],
        ),
        ClaimItem(
            claim_id="C04",
            claim_text="P13 相对最强基线 J 改善 >= 3%",
            metric_name="j_improve_vs_strongest_baseline_mean",
            metric_value=f"{float(p13['summary'].get('j_improve_vs_strongest_baseline_mean', 0.0)) * 100.0:.3f}%",
            target=">=3%",
            passed=bool(float(p13["summary"].get("j_improve_vs_strongest_baseline_mean", 0.0)) >= 0.03),
            evidence_paths=[ROOT / "outputs/router_phase13_sota_v1/stats.json"],
        ),
        ClaimItem(
            claim_id="C05",
            claim_text="P13 pooled 显著性达标 (p<0.01, CI 不跨 0)",
            metric_name="pooled_p/ci",
            metric_value=str(
                {
                    "p": p13["summary"].get("pooled_p_value_bootstrap_gt0"),
                    "ci95": p13["summary"].get("pooled_delta_j_ci95"),
                }
            ),
            target="p<0.01 and ci_low>0",
            passed=bool(
                float(p13["summary"].get("pooled_p_value_bootstrap_gt0", 1.0)) < 0.01
                and float(p13["summary"].get("pooled_delta_j_ci95", [0.0, 0.0])[0]) > 0.0
            ),
            evidence_paths=[ROOT / "outputs/router_phase13_sota_v1/stats.json"],
        ),
        ClaimItem(
            claim_id="C06",
            claim_text="P13 风险不劣（ΔV <= 0.5pct）",
            metric_name="risk_delta_vs_strongest_mean_pct",
            metric_value=f"{float(p13['summary'].get('risk_delta_vs_strongest_mean_pct', 0.0)):.3f}",
            target="<=0.5",
            passed=bool(float(p13["summary"].get("risk_delta_vs_strongest_mean_pct", 1e9)) <= 0.5),
            evidence_paths=[ROOT / "outputs/router_phase13_sota_v1/stats.json"],
        ),
        ClaimItem(
            claim_id="C07",
            claim_text="P14 扰动类型与样本规模达标",
            metric_name="stress_type_count_ge_10 + cases_per_type_ge_100",
            metric_value=str(
                {
                    "types": p14["gate_check"].get("stress_type_count_ge_10"),
                    "cases": p14["gate_check"].get("cases_per_type_ge_100"),
                }
            ),
            target="both True",
            passed=bool(
                p14["gate_check"].get("stress_type_count_ge_10", False)
                and p14["gate_check"].get("cases_per_type_ge_100", False)
            ),
            evidence_paths=[
                ROOT / "outputs/router_phase14_stress_v1/stats.json",
                ROOT / "outputs/router_phase14_stress_v1/stress_profile_summary.csv",
            ],
        ),
        ClaimItem(
            claim_id="C08",
            claim_text="P14 Worst-10% 成功率与恢复率达标",
            metric_name="worst10_success + recovery_success",
            metric_value=str(
                {
                    "worst10": p14["summary"].get("worst10_success_rate"),
                    "recovery": p14["summary"].get("recovery_success_rate"),
                }
            ),
            target=">=0.92 and >=0.95",
            passed=bool(
                float(p14["summary"].get("worst10_success_rate", 0.0)) >= 0.92
                and float(p14["summary"].get("recovery_success_rate", 0.0)) >= 0.95
            ),
            evidence_paths=[ROOT / "outputs/router_phase14_stress_v1/stats.json"],
        ),
        ClaimItem(
            claim_id="C09",
            claim_text="P14 灾难性碰撞为 0",
            metric_name="catastrophic_collision_count",
            metric_value=str(p14["summary"].get("catastrophic_collision_count")),
            target="0",
            passed=bool(int(p14["summary"].get("catastrophic_collision_count", 1)) == 0),
            evidence_paths=[ROOT / "outputs/router_phase14_stress_v1/stats.json"],
        ),
        ClaimItem(
            claim_id="C10",
            claim_text="Exp3/Exp4 漂移不退化（<=0.5%）",
            metric_name="exp3_exp4_drift_abs_le_0_5pct",
            metric_value=str(p12["gate_check"].get("exp3_exp4_dE_drift_abs_le_0_5pct")),
            target="True",
            passed=bool(p12["gate_check"].get("exp3_exp4_dE_drift_abs_le_0_5pct", False)),
            evidence_paths=[ROOT / "outputs/router_phase12_realworld_v1/stats.json"],
        ),
        ClaimItem(
            claim_id="C11",
            claim_text="理论闭环 gap <= 2%",
            metric_name="theory_bound_gap_le_2pct",
            metric_value=str(p11["gate_check"].get("theory_bound_gap_le_2pct")),
            target="True",
            passed=bool(p11["gate_check"].get("theory_bound_gap_le_2pct", False)),
            evidence_paths=[ROOT / "outputs/router_phase11_theory_v1/stats.json"],
        ),
        # Step1/2/4 claims.
        ClaimItem(
            claim_id="C12",
            claim_text="P16 相关工作基线 3 类齐备，且统计口径一致",
            metric_name="baseline_family_count_ge_3 + same_protocol_and_budget",
            metric_value=str(
                {
                    "baseline_family_count_ge_3": p16["gate_check"].get("baseline_family_count_ge_3"),
                    "same_protocol_and_budget": p16["gate_check"].get("same_protocol_and_budget"),
                }
            ),
            target="both True",
            passed=bool(
                p16["gate_check"].get("baseline_family_count_ge_3", False)
                and p16["gate_check"].get("same_protocol_and_budget", False)
            ),
            evidence_paths=[
                ROOT / "outputs/router_phase16_related_baselines_v1/stats.json",
                ROOT / "reports/router_phase16_related_baselines_v1.md",
            ],
        ),
        ClaimItem(
            claim_id="C13",
            claim_text="P16 相对相关工作最强 baseline: J 改善>=3%，风险不劣，且 pooled 显著",
            metric_name="J_improve/risk/pooled_significance",
            metric_value=str(
                {
                    "J_improve_vs_best_related_ge_3pct": p16["gate_check"].get("J_improve_vs_best_related_ge_3pct"),
                    "risk_not_worse_deltaV_le_0_5pct": p16["gate_check"].get("risk_not_worse_deltaV_le_0_5pct"),
                    "pooled_p_lt_0_01_and_ci_no_cross_0": p16["gate_check"].get("pooled_p_lt_0_01_and_ci_no_cross_0"),
                }
            ),
            target="all True",
            passed=bool(
                p16["gate_check"].get("J_improve_vs_best_related_ge_3pct", False)
                and p16["gate_check"].get("risk_not_worse_deltaV_le_0_5pct", False)
                and p16["gate_check"].get("pooled_p_lt_0_01_and_ci_no_cross_0", False)
            ),
            evidence_paths=[ROOT / "outputs/router_phase16_related_baselines_v1/stats.json"],
        ),
        ClaimItem(
            claim_id="C14",
            claim_text="P17 单一 policy artifact 封口 + 闭环无显著退化",
            metric_name="policy_single_source_of_truth + policy_vs_rule_no_regression_large",
            metric_value=str(
                {
                    "policy_single_source_of_truth": p17["gate_check"].get("policy_single_source_of_truth"),
                    "policy_vs_rule_no_regression_large": p17["gate_check"].get("policy_vs_rule_no_regression_large"),
                }
            ),
            target="both True",
            passed=bool(
                p17["gate_check"].get("policy_single_source_of_truth", False)
                and p17["gate_check"].get("policy_vs_rule_no_regression_large", False)
            ),
            evidence_paths=[
                ROOT / "outputs/router_phase17_policy_alignment_v1/stats.json",
                ROOT / "reports/router_phase17_policy_alignment_v1.md",
                ROOT / "artifacts/router_policy_v1/policy.json",
                ROOT / "artifacts/router_policy_v1/POLICY.sha256",
            ],
        ),
        ClaimItem(
            claim_id="C15",
            claim_text="P19 新增 secondary 指标并完成 5 seeds + OOD 分析，且 router 不显著变差",
            metric_name="secondary_metric_added + router_not_worse_on_secondary",
            metric_value=str(
                {
                    "secondary_metric_added": p19["gate_check"].get("secondary_metric_added"),
                    "secondary_results_reported_all_seeds": p19["gate_check"].get("secondary_results_reported_all_seeds"),
                    "router_not_worse_on_secondary": p19["gate_check"].get("router_not_worse_on_secondary"),
                    "proxy_validity_explained": p19["gate_check"].get("proxy_validity_explained"),
                }
            ),
            target="all True",
            passed=bool(all(bool(v) for v in p19["gate_check"].values())),
            evidence_paths=[
                ROOT / "outputs/router_phase19_metrics_extension_v1/stats.json",
                ROOT / "reports/router_phase19_metrics_extension_v1.md",
                ROOT / "paper/tables_router_v6/table_secondary_metrics.csv",
            ],
        ),
        # Step6 (Phase21): method abstraction + runnable demo.
        ClaimItem(
            claim_id="C16",
            claim_text="P21 minimal demo 可在 10s 内运行且保持单调安全",
            metric_name="demo_runs_under_10s + probe_is_monotone_safe",
            metric_value=str(p21.get("gate_check", {})),
            target="both True",
            passed=bool(
                p21.get("gate_check", {}).get("demo_runs_under_10s", False)
                and p21.get("gate_check", {}).get("probe_is_monotone_safe", False)
            ),
            evidence_paths=[
                ROOT / "outputs/router_phase21_neurips_positioning_v1/stats.json",
                ROOT / "reports/router_phase21_neurips_positioning_v1.md",
                ROOT / "docs/neurips_method_v1.md",
                ROOT / "utils/router_method_core.py",
            ],
        ),
        # Step7 (Phase22): direct baselines.
        ClaimItem(
            claim_id="C17",
            claim_text="P22 direct baselines (CDT/CRC) 在同协议下可复现且通过 gate",
            metric_name="gate_check",
            metric_value=str(p22.get("gate_check", {})),
            target="all True",
            passed=bool(all(bool(v) for v in p22.get("gate_check", {}).values())),
            evidence_paths=[
                ROOT / "outputs/router_phase22_direct_baselines_v1/stats.json",
                ROOT / "reports/router_phase22_direct_baselines_v1.md",
                ROOT / "paper/tables_router_v7/table_phase22_direct_baselines.csv",
            ],
        ),
        # Step8 (Phase23): multi-arm routing.
        ClaimItem(
            claim_id="C18",
            claim_text="P23 portfolio router: K>=3 + 风险约束全 seeds 成立 + 存在 Pareto 优势区域",
            metric_name="gate_check",
            metric_value=str(p23.get("gate_check", {})),
            target="all True",
            passed=bool(all(bool(v) for v in p23.get("gate_check", {}).values())),
            evidence_paths=[
                ROOT / "outputs/router_phase23_portfolio_v1/stats.json",
                ROOT / "reports/router_phase23_portfolio_v1.md",
                ROOT / "paper/tables_router_v7/table_phase23_portfolio.csv",
                ROOT / "paper/figures_router_v7/fig_portfolio_tradeoff.svg",
                ROOT / "outputs/router_phase23_midnet_arm_full_tiny_b64_v1/stats.json",
            ],
        ),
        # Step9 (Phase24): theory v3.
        ClaimItem(
            claim_id="C19",
            claim_text="P24 theory v3: 非平凡结论 + 冻结 seeds/OOD families 上逐条校验通过 + slack 合理",
            metric_name="gate_check",
            metric_value=str(p24.get("gate_check", {})),
            target="all True",
            passed=bool(all(bool(v) for v in p24.get("gate_check", {}).values())),
            evidence_paths=[
                ROOT / "outputs/router_phase24_theory_v3/stats.json",
                ROOT / "reports/router_phase24_theory_v3.md",
                ROOT / "docs/router_theory_v3.md",
                ROOT / "docs/router_theory_v3_appendix.md",
                ROOT / "outputs/router_phase24_theory_v3/seed_checks.csv",
                ROOT / "outputs/router_phase24_theory_v3/shift_bounds.csv",
            ],
        ),
        # Step10 (Phase25): generalization.
        ClaimItem(
            claim_id="C20",
            claim_text="P25 跨设置泛化：>=2 设置 + 风险控制成立 + 主要趋势不翻车",
            metric_name="gate_check",
            metric_value=str(p25.get("gate_check", {})),
            target="all True",
            passed=bool(all(bool(v) for v in p25.get("gate_check", {}).values())),
            evidence_paths=[
                ROOT / "outputs/router_phase25_generalization_v1/stats.json",
                ROOT / "reports/router_phase25_generalization_v1.md",
                ROOT / "paper/figures_router_v7/fig_generalization_mp.svg",
                ROOT / "paper/figures_router_v7/fig_generalization_csm.svg",
            ],
        ),
    ]
    return claims


def _write_claim_matrix(path: Path, claims: list[ClaimItem]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "claim_id",
                "claim_text",
                "metric_name",
                "metric_value",
                "target",
                "passed",
                "evidence_paths",
            ]
        )
        for c in claims:
            w.writerow(
                [
                    c.claim_id,
                    c.claim_text,
                    c.metric_name,
                    c.metric_value,
                    c.target,
                    str(bool(c.passed)),
                    ";".join(str(p.relative_to(ROOT)) for p in c.evidence_paths),
                ]
            )


def _write_report(path: Path, audit: dict) -> None:
    lines: list[str] = []
    lines.append("# Router Phase26 Camera-Ready V3 Report")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Runtime: `{audit['runtime_hours']:.3f} h`")
    lines.append(f"- Repro runtime estimate: `{audit['runtime_estimate_hours']:.3f} h`")
    lines.append(f"- Hash consistency: `{audit['hash_consistency_rate'] * 100.0:.2f}%`")
    lines.append(f"- Claim coverage: `{audit['claim_coverage_rate'] * 100.0:.2f}%`")
    lines.append(f"- Blockers: `{audit['blocker_count']}`")
    lines.append("")
    lines.append("## Gate Check")
    for k, v in audit["gate_check"].items():
        lines.append(f"- `{k}`: `{v}`")
    lines.append("")
    lines.append("## Artifacts")
    for k, v in audit["artifacts"].items():
        lines.append(f"- `{k}`: `{v}`")
    lines.append("")
    lines.append("## Blockers")
    if audit["blockers"]:
        for b in audit["blockers"]:
            lines.append(f"- {b}")
    else:
        lines.append("- `None (0 blocker)`")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_checklist(path: Path, audit: dict, claims: list[ClaimItem]) -> None:
    lines: list[str] = []
    lines.append("# Final Submission Checklist (V3)")
    lines.append("")
    lines.append("## Gate Status")
    for k, v in audit["gate_check"].items():
        lines.append(f"- `{k}`: `{v}`")
    lines.append("")
    lines.append("## Claim-to-Evidence")
    lines.append("| claim_id | pass | metric | target | evidence |")
    lines.append("|---|---:|---|---|---|")
    for c in claims:
        ev = ", ".join(str(p.relative_to(ROOT)) for p in c.evidence_paths)
        lines.append(f"| {c.claim_id} | {bool(c.passed)} | {c.metric_value} | {c.target} | {ev} |")
    lines.append("")
    lines.append("## Reproduction")
    lines.append("- One-command: `bash artifacts/router_camera_ready_v3/reproduce_main_tables_figures.sh`")
    lines.append("- Container: `docker build -t router-camera-ready-v3 -f artifacts/router_camera_ready_v3/Dockerfile .`")
    lines.append("- Estimated cold-start runtime: `{:.3f} h` (target <= 48 h)".format(audit["runtime_estimate_hours"]))
    lines.append("")
    lines.append("## Hash Audit")
    lines.append(
        "- Hash consistency: `{:.2f}%` ({} / {})".format(
            audit["hash_consistency_rate"] * 100.0,
            audit["hash_match_count"],
            audit["hash_total_count"],
        )
    )
    lines.append("- Manifest: `artifacts/router_camera_ready_v3/MANIFEST.sha256`")
    lines.append("")
    lines.append("## Notes")
    lines.append("- Step3 (real-hardware longrun) is excluded from NeurIPS/ICML readiness; required for Top-Journal.")
    lines.append("")
    lines.append("## Blockers")
    if audit["blockers"]:
        for b in audit["blockers"]:
            lines.append(f"- {b}")
    else:
        lines.append("- `None (0 blocker)`")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_final_v3(final_dir: Path, artifact_dir: Path) -> Path:
    # Rebuild outputs/final_v3 by copying outputs/final and overlaying new phases + v3 bundle.
    src_final = ROOT / "outputs" / "final"
    if not src_final.exists():
        raise FileNotFoundError(src_final)
    if final_dir.exists():
        shutil.rmtree(final_dir)
    shutil.copytree(src_final, final_dir, dirs_exist_ok=True)

    # Sync paper + reports + docs from source-of-truth.
    for name in ("paper", "reports", "docs"):
        dst = final_dir / name
        if dst.exists():
            shutil.rmtree(dst)
        _copytree_overwrite(ROOT / name, dst)

    # Add required phase outputs (Step1/2/4 + Step6~10).
    for d in [
        ROOT / "outputs" / "router_phase16_related_baselines_v1",
        ROOT / "outputs" / "router_phase17_policy_alignment_v1",
        ROOT / "outputs" / "router_phase19_metrics_extension_v1",
        ROOT / "outputs" / "router_phase21_neurips_positioning_v1",
        ROOT / "outputs" / "router_phase22_direct_baselines_v1",
        ROOT / "outputs" / "router_phase23_midnet_arm_full_tiny_b64_v1",
        ROOT / "outputs" / "router_phase23_portfolio_v1",
        ROOT / "outputs" / "router_phase24_theory_v3",
        ROOT / "outputs" / "router_phase25_generalization_v1",
    ]:
        _copytree_overwrite(d, final_dir / d.name)

    # Add policy artifact for self-contained audit/repro.
    _copytree_overwrite(ROOT / "artifacts" / "router_policy_v1", final_dir / "artifacts" / "router_policy_v1")

    # Add camera-ready v3 bundle.
    _copytree_overwrite(artifact_dir, final_dir / "router_camera_ready_v3")

    # Build manifest.json for final_v3.
    phases: dict[str, Path] = {
        "phase7": final_dir / "router_phase7_v1" / "stats.json",
        "phase8": final_dir / "router_phase8_strict_v1" / "stats.json",
        "phase9": final_dir / "router_phase9_bench_v1" / "stats.json",
        "phase10": final_dir / "router_phase10_system_v1" / "stats.json",
        "phase11": final_dir / "router_phase11_theory_v1" / "stats.json",
        "phase12": final_dir / "router_phase12_realworld_v1" / "stats.json",
        "phase13": final_dir / "router_phase13_sota_v1" / "stats.json",
        "phase14": final_dir / "router_phase14_stress_v1" / "stats.json",
        "phase16": final_dir / "router_phase16_related_baselines_v1" / "stats.json",
        "phase17": final_dir / "router_phase17_policy_alignment_v1" / "stats.json",
        "phase19": final_dir / "router_phase19_metrics_extension_v1" / "stats.json",
        "phase21": final_dir / "router_phase21_neurips_positioning_v1" / "stats.json",
        "phase22": final_dir / "router_phase22_direct_baselines_v1" / "stats.json",
        "phase23": final_dir / "router_phase23_portfolio_v1" / "stats.json",
        "phase24": final_dir / "router_phase24_theory_v3" / "stats.json",
        "phase25": final_dir / "router_phase25_generalization_v1" / "stats.json",
        "phase15_audit_v1": final_dir / "router_camera_ready_v1" / "audit_summary.json",
        "phase26_audit_v3": final_dir / "router_camera_ready_v3" / "audit_summary.json",
    }
    # Optionally include v2 audit when present.
    p20 = final_dir / "router_camera_ready_v2" / "audit_summary.json"
    if p20.exists():
        phases["phase20_audit_v2"] = p20

    stats_out: dict[str, dict] = {}
    for name, p in phases.items():
        if not p.exists():
            continue
        obj = _load_json(p)
        runtime_hours = float(obj.get("runtime_hours", 0.0))
        if runtime_hours <= 0.0 and "runtime_seconds" in obj:
            runtime_hours = float(obj.get("runtime_seconds", 0.0)) / 3600.0
        if runtime_hours <= 0.0 and "runtime_s" in obj:
            runtime_hours = float(obj.get("runtime_s", 0.0)) / 3600.0
        stats_out[name] = {
            "path": str(p.relative_to(final_dir)),
            "gate_check": obj.get("gate_check", {}),
            "runtime_hours": float(runtime_hours),
            "version": obj.get("version", ""),
        }

    # NOTE: Do not include `manifest.json` itself in key-file hashes (self-hash is ill-defined).
    key_rel_paths = [
        "router_camera_ready_v3/audit_summary.json",
        "router_camera_ready_v3/MANIFEST.sha256",
        "router_phase21_neurips_positioning_v1/stats.json",
        "router_phase22_direct_baselines_v1/stats.json",
        "router_phase23_portfolio_v1/stats.json",
        "router_phase24_theory_v3/stats.json",
        "router_phase25_generalization_v1/stats.json",
        "reports/router_phase25_generalization_v1.md",
        "paper/figures_router_v7/fig_generalization_mp.svg",
        "paper/figures_router_v7/fig_generalization_csm.svg",
        "docs/router_protocol_v1.md",
        "docs/neurips_method_v1.md",
        "docs/router_theory_v3.md",
        "docs/router_theory_v3_appendix.md",
    ]
    key_files: list[dict] = []
    for rel in key_rel_paths:
        p = final_dir / rel
        if not p.exists() or p.is_dir():
            continue
        key_files.append({"path": str(rel), "sha256": _sha256(p)})

    manifest = {
        "bundle": str(final_dir),
        "created_at": time.strftime("%Y-%m-%d"),
        "stats": stats_out,
        "key_files": key_files,
    }
    out_manifest = final_dir / "manifest.json"
    out_manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return out_manifest


def main() -> None:
    args = parse_args()
    t0 = time.perf_counter()

    artifact_dir = Path(args.artifact_dir)
    bundle = _write_repro_bundle(artifact_dir)
    evidence_dir = bundle["evidence_dir"]

    # Load phase stats needed for claims + runtime estimate.
    p7 = _load_json(ROOT / "outputs/router_phase7_v1/stats.json")
    p8 = _load_json(ROOT / "outputs/router_phase8_strict_v1/stats.json")
    p9 = _load_json(ROOT / "outputs/router_phase9_bench_v1/stats.json")
    p10 = _load_json(ROOT / "outputs/router_phase10_system_v1/stats.json")
    p11 = _load_json(ROOT / "outputs/router_phase11_theory_v1/stats.json")
    p12 = _load_json(ROOT / "outputs/router_phase12_realworld_v1/stats.json")
    p13 = _load_json(ROOT / "outputs/router_phase13_sota_v1/stats.json")
    p14 = _load_json(ROOT / "outputs/router_phase14_stress_v1/stats.json")
    p16 = _load_json(ROOT / "outputs/router_phase16_related_baselines_v1/stats.json")
    p17 = _load_json(ROOT / "outputs/router_phase17_policy_alignment_v1/stats.json")
    p19 = _load_json(ROOT / "outputs/router_phase19_metrics_extension_v1/stats.json")
    p21 = _load_json(ROOT / "outputs/router_phase21_neurips_positioning_v1/stats.json")
    p22 = _load_json(ROOT / "outputs/router_phase22_direct_baselines_v1/stats.json")
    p23 = _load_json(ROOT / "outputs/router_phase23_portfolio_v1/stats.json")
    p24 = _load_json(ROOT / "outputs/router_phase24_theory_v3/stats.json")
    p25 = _load_json(ROOT / "outputs/router_phase25_generalization_v1/stats.json")

    stats_map = {
        "p7": p7,
        "p8": p8,
        "p9": p9,
        "p10": p10,
        "p11": p11,
        "p12": p12,
        "p13": p13,
        "p14": p14,
        "p16": p16,
        "p17": p17,
        "p19": p19,
        "p21": p21,
        "p22": p22,
        "p23": p23,
        "p24": p24,
        "p25": p25,
    }

    required = _required_paths_v3()
    missing: list[str] = []
    copied_rows: list[tuple[str, str, str, bool]] = []

    for src in required:
        if not src.exists() or src.is_dir():
            missing.append(str(src.relative_to(ROOT)))
            continue
        rel = src.relative_to(ROOT)
        dst = evidence_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        h_src = _sha256(src)
        h_dst = _sha256(dst)
        copied_rows.append((str(rel), h_src, h_dst, h_src == h_dst))

    manifest = artifact_dir / "MANIFEST.sha256"
    with manifest.open("w", encoding="utf-8") as f:
        for rel, h_src, _, ok in copied_rows:
            if ok:
                f.write(f"{h_src}  evidence/{rel}\n")

    hash_csv = artifact_dir / "hash_compare.csv"
    with hash_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["relative_path", "sha256_src", "sha256_copy", "match"])
        for rel, h_src, h_dst, ok in copied_rows:
            w.writerow([rel, h_src, h_dst, str(ok)])

    claims = _build_claims(
        {
            "p11": p11,
            "p12": p12,
            "p13": p13,
            "p14": p14,
            "p16": p16,
            "p17": p17,
            "p19": p19,
            "p21": p21,
            "p22": p22,
            "p23": p23,
            "p24": p24,
            "p25": p25,
        }
    )
    claim_csv = artifact_dir / "claim_to_evidence.csv"
    _write_claim_matrix(claim_csv, claims)

    claim_cover = 0
    for c in claims:
        ev_ok = all(p.exists() for p in c.evidence_paths)
        if ev_ok:
            claim_cover += 1
    claim_coverage = float(claim_cover / max(len(claims), 1))

    hash_total = len(copied_rows)
    hash_match = sum(1 for _, _, _, ok in copied_rows if ok)
    hash_consistency = float(hash_match / max(hash_total, 1))

    runtime_est = _runtime_estimate_hours(stats_map)

    blockers: list[str] = []
    if missing:
        blockers.append(f"missing required files: {len(missing)}")
    failed_claims = [c.claim_id for c in claims if not c.passed]
    if failed_claims:
        blockers.append(f"failed claims: {', '.join(failed_claims)}")
    if hash_consistency < 1.0 - 1e-12:
        blockers.append("hash consistency < 100%")
    if claim_coverage < 1.0 - 1e-12:
        blockers.append("claim coverage < 100%")
    if runtime_est > float(args.runtime_target_hours):
        blockers.append(f"runtime estimate {runtime_est:.3f}h exceeds target {args.runtime_target_hours:.3f}h")

    gate = {
        "cold_start_runtime_le_48h": bool(runtime_est <= float(args.runtime_target_hours)),
        "hash_consistency_100pct": bool(hash_consistency >= 1.0 - 1e-12),
        "claim_coverage_100pct": bool(claim_coverage >= 1.0 - 1e-12),
        "audit_blocker_zero": bool(len(blockers) == 0),
    }

    audit = {
        "version": "router_phase26_camera_ready_v3",
        "runtime_hours": float((time.perf_counter() - t0) / 3600.0),
        "runtime_estimate_hours": float(runtime_est),
        "runtime_target_hours": float(args.runtime_target_hours),
        "hash_total_count": int(hash_total),
        "hash_match_count": int(hash_match),
        "hash_consistency_rate": float(hash_consistency),
        "claim_total_count": int(len(claims)),
        "claim_covered_count": int(claim_cover),
        "claim_coverage_rate": float(claim_coverage),
        "blocker_count": int(len(blockers)),
        "blockers": blockers,
        "missing_files": missing,
        "failed_claims": failed_claims,
        "gate_check": gate,
        "artifacts": {
            "bundle_dir": str(artifact_dir),
            "manifest_sha256": str(manifest),
            "hash_compare_csv": str(hash_csv),
            "claim_to_evidence_csv": str(claim_csv),
            "dockerfile": str(bundle["dockerfile"]),
            "reproduce_sh": str(bundle["repro_sh"]),
            "requirements_lock": str(bundle["requirements_lock"]),
            "bundle_readme": str(bundle["readme"]),
            "report_md": str(args.report_md),
            "checklist_md": str(args.checklist_md),
            "final_manifest_json": str(Path(args.final_dir) / "manifest.json"),
        },
    }

    audit_json = artifact_dir / "audit_summary.json"
    audit_json.write_text(json.dumps(audit, indent=2), encoding="utf-8")

    _write_report(Path(args.report_md), audit=audit)
    _write_checklist(Path(args.checklist_md), audit=audit, claims=claims)

    # Build outputs/final_v3 bundle + manifest.json.
    out_manifest = _build_final_v3(Path(args.final_dir), artifact_dir)

    print(f"[phase26] audit={audit_json}")
    print(f"[phase26] report={args.report_md}")
    print(f"[phase26] checklist={args.checklist_md}")
    print(f"[phase26] final_manifest={out_manifest}")
    print(f"[phase26] gate={gate}")

    if bool(args.enforce_gate) and not all(gate.values()):
        raise RuntimeError("Phase-26 gate failed. Check artifacts/router_camera_ready_v3/audit_summary.json")


if __name__ == "__main__":
    main()
