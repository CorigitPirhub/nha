from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Phase27 strict audit + recovery runner: strict (calib-only selection/search) vs legacy (test tuning diagnostic), "
        "plus final_v4_strict bundle."
    )
    p.add_argument("--seeds", type=str, default="7,11,19,23,31")
    p.add_argument("--device", type=str, default="cpu")
    p.add_argument("--checkpoint", type=Path, default=Path("outputs/checkpoints/exp3_final_manual_v11b.pt"))
    p.add_argument("--benchmark-root", type=Path, default=Path("data/benchmark"))
    p.add_argument("--dataset-root", type=Path, default=Path("data/router_phase9_public_v1"))

    p.add_argument(
        "--reuse-common-dir",
        type=Path,
        default=Path("outputs/router_phase9_bench_v2_calibsplit/common"),
        help="If counterfactual parquets are missing for a run, copy them from this directory to avoid recomputation.",
    )

    # Strict (paper-valid) defaults: use the Phase-8 recovery policy (knapsack_lcb + signed gain + cost-aware feature).
    p.add_argument("--strict-phase9-out", type=Path, default=Path("outputs/router_phase9_bench_v6_strict_knapsack"))
    p.add_argument("--legacy-phase9-out", type=Path, default=Path("outputs/router_phase9_bench_v3_legacy_diag"))
    p.add_argument("--strict-phase13-out", type=Path, default=Path("outputs/router_phase13_sota_v4_strict_knapsack"))
    p.add_argument("--legacy-phase13-out", type=Path, default=Path("outputs/router_phase13_sota_v3_legacy_diag"))
    p.add_argument("--strict-phase22-out", type=Path, default=Path("outputs/router_phase22_direct_baselines_v4_strict_knapsack"))
    p.add_argument("--legacy-phase22-out", type=Path, default=Path("outputs/router_phase22_direct_baselines_v3_legacy_diag"))

    p.add_argument("--strict-tables-dir", type=Path, default=Path("paper/tables_router_v11_strict_knapsack"))
    p.add_argument("--legacy-tables-dir", type=Path, default=Path("paper/tables_router_v8_legacy_diag"))
    p.add_argument("--strict-audit-report-md", type=Path, default=Path("reports/router_strict_audit_v1.md"))
    p.add_argument("--ab-table-csv", type=Path, default=Path("paper/tables_router_v11_strict_knapsack/table_phase27_leakage_ab.csv"))

    # Forwarded strict Phase-8 knobs (for reproduction; never tuned on test).
    p.add_argument("--strict-phase8-tune-violation-margin", type=float, default=0.02)
    p.add_argument("--strict-phase8-tune-ci-margin", type=float, default=0.015)
    p.add_argument("--strict-phase8-probe-include-cost-feature", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument(
        "--strict-phase8-probe-selection-mode",
        type=str,
        default="knapsack_lcb",
        choices=["grid_search", "conformal_lcb", "knapsack_lcb"],
    )
    p.add_argument("--strict-phase8-probe-lcb-alpha", type=float, default=0.25)

    p.add_argument("--final-dir", type=Path, default=Path("outputs/final_v4_strict"))
    p.add_argument("--force", action="store_true")
    p.add_argument("--skip-legacy", action=argparse.BooleanOptionalAction, default=False)
    p.add_argument("--enforce-gate", action=argparse.BooleanOptionalAction, default=True)
    return p.parse_args()


def _parse_seeds(raw: str) -> list[int]:
    out: list[int] = []
    for tok in str(raw).split(","):
        tok = tok.strip()
        if tok:
            out.append(int(tok))
    if not out:
        raise ValueError("Empty seed list.")
    return out


def _run(cmd: list[str], log_path: Path, env_extra: dict[str, str] | None = None) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"\n$ {' '.join(cmd)}\n")
        f.flush()
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        f.write(proc.stdout)
        f.flush()
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(cmd)}; see {log_path}")


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


def _copytree_overwrite(src: Path, dst: Path) -> None:
    if not src.exists():
        raise FileNotFoundError(src)
    if src.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return
    shutil.copytree(src, dst, dirs_exist_ok=True)


def _ensure_counterfactual_common(out_dir: Path, reuse_common: Path) -> None:
    common = out_dir / "common"
    common.mkdir(parents=True, exist_ok=True)
    for name in [
        "router_counterfactual_calib.parquet",
        "router_counterfactual_test.parquet",
        "router_counterfactual_calib_report.json",
        "router_counterfactual_test_report.json",
    ]:
        dst = common / name
        if dst.exists():
            continue
        src = reuse_common / name
        if src.exists():
            shutil.copy2(src, dst)

    # Optional: reuse risk features to avoid recomputation in CPU-only environments.
    risk_dst = common / "risk"
    risk_src = reuse_common / "risk"
    if (not risk_dst.exists()) and risk_src.exists():
        shutil.copytree(risk_src, risk_dst, dirs_exist_ok=True)

    # Optional: reuse probe feature caches (Phase-6 feature extractor) if available.
    reuse_phase9_root = reuse_common.parent
    probe_src = reuse_phase9_root / "router_eval" / "common"
    if probe_src.exists():
        probe_dst = out_dir / "router_eval" / "common"
        probe_dst.mkdir(parents=True, exist_ok=True)
        for name in ["probe_features_calib.parquet", "probe_features_test.parquet"]:
            dst = probe_dst / name
            if dst.exists():
                continue
            src = probe_src / name
            if src.exists():
                shutil.copy2(src, dst)


def _run_phase9(
    *,
    variant: str,
    out_dir: Path,
    report_md: Path,
    tables_dir: Path,
    seeds: str,
    device: str,
    checkpoint: Path,
    benchmark_root: Path,
    dataset_root: Path,
    reuse_common: Path,
    phase8_calib_split_mode: str,
    phase8_conformal_select_on: str,
    phase8_probe_search_on: str,
    phase8_strict_tune_violation_margin: float,
    phase8_strict_tune_ci_margin: float,
    phase8_probe_include_cost_feature: bool,
    phase8_probe_selection_mode: str,
    phase8_probe_lcb_alpha: float,
    force: bool,
) -> Path:
    _ensure_counterfactual_common(out_dir, reuse_common=reuse_common)
    run_log = out_dir / "run.log"
    cmd = [
        str(Path(sys.executable)),
        "scripts/run_router_phase9_bench.py",
        "--seeds",
        str(seeds),
        "--device",
        str(device),
        "--checkpoint",
        str(checkpoint),
        "--benchmark-root",
        str(benchmark_root),
        "--dataset-root",
        str(dataset_root),
        "--out-dir",
        str(out_dir),
        "--report-md",
        str(report_md),
        "--risk-report-md",
        str(report_md.with_name(f"{report_md.stem}_risk.md")),
        "--router-eval-report-md",
        str(report_md.with_name(f"{report_md.stem}_router_eval.md")),
        "--tables-dir",
        str(tables_dir),
        "--calib-split-mode",
        str(phase8_calib_split_mode),
        "--conformal-select-on",
        str(phase8_conformal_select_on),
        "--probe-search-on",
        str(phase8_probe_search_on),
        "--phase8-strict-tune-violation-margin",
        str(float(phase8_strict_tune_violation_margin)),
        "--phase8-strict-tune-ci-margin",
        str(float(phase8_strict_tune_ci_margin)),
        "--phase8-probe-include-cost-feature" if bool(phase8_probe_include_cost_feature) else "--no-phase8-probe-include-cost-feature",
        "--phase8-probe-selection-mode",
        str(phase8_probe_selection_mode),
        "--phase8-probe-lcb-alpha",
        str(float(phase8_probe_lcb_alpha)),
        "--no-enforce-gate",
    ]
    if bool(force):
        cmd.append("--force")
    _run(cmd, log_path=run_log)
    stats = out_dir / "stats.json"
    if not stats.exists():
        raise FileNotFoundError(stats)
    print(f"[phase27][{variant}] phase9 stats: {stats}")
    return stats


def _run_phase13(
    *,
    variant: str,
    phase9_root: Path,
    out_dir: Path,
    report_md: Path,
    tables_dir: Path,
    external_baselines_csv: Path,
    force: bool,
) -> Path:
    run_log = out_dir / "run.log"
    cmd = [
        str(Path(sys.executable)),
        "scripts/run_router_phase13_sota.py",
        "--phase9-root",
        str(phase9_root),
        "--external-baselines-csv",
        str(external_baselines_csv),
        "--out-dir",
        str(out_dir),
        "--report-md",
        str(report_md),
        "--tables-dir",
        str(tables_dir),
        "--no-enforce-gate",
    ]
    # Phase13 has no internal caching; `--force` is kept for interface symmetry.
    _run(cmd, log_path=run_log)
    stats = out_dir / "stats.json"
    if not stats.exists():
        raise FileNotFoundError(stats)
    print(f"[phase27][{variant}] phase13 stats: {stats}")
    return stats


def _run_phase22(
    *,
    variant: str,
    phase9_root: Path,
    out_dir: Path,
    report_md: Path,
    tables_dir: Path,
    force: bool,
) -> Path:
    run_log = out_dir / "run.log"
    cmd = [
        str(Path(sys.executable)),
        "scripts/run_router_phase22_direct_baselines.py",
        "--phase9-root",
        str(phase9_root),
        "--out-dir",
        str(out_dir),
        "--report-md",
        str(report_md),
        "--tables-dir",
        str(tables_dir),
        "--no-enforce-gate",
    ]
    _run(cmd, log_path=run_log)
    stats = out_dir / "stats.json"
    if not stats.exists():
        raise FileNotFoundError(stats)
    print(f"[phase27][{variant}] phase22 stats: {stats}")
    return stats


def _ab_summary(*, strict: dict, legacy: dict) -> pd.DataFrame:
    rows: list[dict] = []

    def add(phase: str, metric: str, s: float | str, l: float | str) -> None:
        rec: dict[str, object] = {"phase": phase, "metric": metric, "strict": s, "legacy_diag": l}
        if isinstance(s, (int, float)) and isinstance(l, (int, float)):
            rec["strict_minus_legacy"] = float(s) - float(l)
        rows.append(rec)

    add("phase9", "pooled_mean_delta_j", float(strict["p9"]["pooled"]["mean_delta_j"]), float(legacy["p9"]["pooled"]["mean_delta_j"]))
    add("phase9", "p_value_bootstrap_gt0", float(strict["p9"]["pooled"]["p_value_bootstrap_gt0"]), float(legacy["p9"]["pooled"]["p_value_bootstrap_gt0"]))
    add("phase9", "ci95_low", float(strict["p9"]["pooled"]["ci95"][0]), float(legacy["p9"]["pooled"]["ci95"][0]))
    add("phase9", "ci95_high", float(strict["p9"]["pooled"]["ci95"][1]), float(legacy["p9"]["pooled"]["ci95"][1]))

    add(
        "phase13",
        "j_improve_vs_strongest_baseline_mean",
        float(strict["p13"]["summary"]["j_improve_vs_strongest_baseline_mean"]),
        float(legacy["p13"]["summary"]["j_improve_vs_strongest_baseline_mean"]),
    )
    add(
        "phase13",
        "pooled_p_value_bootstrap_gt0",
        float(strict["p13"]["summary"]["pooled_p_value_bootstrap_gt0"]),
        float(legacy["p13"]["summary"]["pooled_p_value_bootstrap_gt0"]),
    )
    add(
        "phase13",
        "pooled_ci95_low",
        float(strict["p13"]["summary"]["pooled_delta_j_ci95"][0]),
        float(legacy["p13"]["summary"]["pooled_delta_j_ci95"][0]),
    )
    add(
        "phase13",
        "pooled_ci95_high",
        float(strict["p13"]["summary"]["pooled_delta_j_ci95"][1]),
        float(legacy["p13"]["summary"]["pooled_delta_j_ci95"][1]),
    )

    add(
        "phase22",
        "j_improve_vs_best_direct_mean_pct",
        float(strict["p22"]["summary"]["j_improve_vs_best_direct_mean"]),
        float(legacy["p22"]["summary"]["j_improve_vs_best_direct_mean"]),
    )
    add(
        "phase22",
        "pooled_p_value_bootstrap_gt0",
        float(strict["p22"]["summary"]["pooled_p_value_bootstrap_gt0"]),
        float(legacy["p22"]["summary"]["pooled_p_value_bootstrap_gt0"]),
    )
    add(
        "phase22",
        "best_direct_baseline",
        str(strict["p22"]["best_direct_baseline"]),
        str(legacy["p22"]["best_direct_baseline"]),
    )

    return pd.DataFrame(rows)


def _strict_gate_summary(p9: dict, p13: dict, p22: dict) -> dict[str, bool]:
    p9_ok = (
        float(p9["pooled"]["mean_delta_j"]) > 0.0
        and float(p9["pooled"]["p_value_bootstrap_gt0"]) < 0.01
        and float(p9["pooled"]["ci95"][0]) > 0.0
    )
    p13_ok = bool(all(bool(v) for v in p13.get("gate_check", {}).values())) if isinstance(p13.get("gate_check", None), dict) else False
    # Phase22 "alignment honest" accepts either significant win OR an explicit reframe in the strict audit report.
    p22_sig = bool(p22.get("gate_check", {}).get("main_result_significant", False))
    return {
        "phase9_gain_significant": bool(p9_ok),
        "phase13_sota_significant": bool(p13_ok),
        "phase22_main_result_significant": bool(p22_sig),
    }


def _write_strict_audit_report(
    *,
    path: Path,
    strict: dict,
    legacy: dict | None,
    ab_df: pd.DataFrame | None,
    strict_gates: dict[str, bool],
    strict_tables_dir: Path,
    legacy_tables_dir: Path | None,
) -> None:
    lines: list[str] = []
    lines.append("# Router Strict Audit Report (Phase27, v1)")
    lines.append("")
    lines.append("## Protocol")
    lines.append("- Strict: select/search only on `calib_train/calib_val`; `test` is used once for final evaluation.")
    lines.append("- Legacy (diagnostic): allows `test`-set tuning in Phase-8 (conformal/probe). **Not** valid for main claims.")
    lines.append("")
    lines.append("## Strict Results")
    lines.append(f"- Phase9 pooled mean ΔJ (P5 - router): `{float(strict['p9']['pooled']['mean_delta_j']):.6f}`")
    lines.append(
        f"- Phase9 pooled 95% CI: `[{float(strict['p9']['pooled']['ci95'][0]):.6f}, {float(strict['p9']['pooled']['ci95'][1]):.6f}]`"
    )
    lines.append(f"- Phase9 p_boot(gt0): `{float(strict['p9']['pooled']['p_value_bootstrap_gt0']):.6e}`")
    lines.append(
        f"- Phase13 mean J-improve vs strongest baseline: `{float(strict['p13']['summary']['j_improve_vs_strongest_baseline_mean']) * 100.0:.3f}%`"
    )
    lines.append(
        f"- Phase22 mean J-improve vs best direct baseline: `{float(strict['p22']['summary']['j_improve_vs_best_direct_mean']):.3f}%` "
        f"(best direct=`{strict['p22']['best_direct_baseline']}`)"
    )
    lines.append("")
    lines.append("## Gate Summary (Strict)")
    for k, v in strict_gates.items():
        lines.append(f"- `{k}`: `{bool(v)}`")
    lines.append("")

    if legacy is not None and ab_df is not None:
        lines.append("## Leakage A/B (Legacy vs Strict)")
        lines.append(f"- Strict tables: `{strict_tables_dir}`")
        if legacy_tables_dir is not None:
            lines.append(f"- Legacy tables: `{legacy_tables_dir}`")
        lines.append("")
        show = ab_df.copy()
        # Keep report compact: show the core metrics only.
        keep = [
            ("phase9", "pooled_mean_delta_j"),
            ("phase9", "p_value_bootstrap_gt0"),
            ("phase13", "j_improve_vs_strongest_baseline_mean"),
            ("phase13", "pooled_p_value_bootstrap_gt0"),
            ("phase22", "j_improve_vs_best_direct_mean_pct"),
            ("phase22", "pooled_p_value_bootstrap_gt0"),
        ]
        mask = pd.Series(False, index=show.index)
        for ph, met in keep:
            mask = mask | ((show["phase"].astype(str) == ph) & (show["metric"].astype(str) == met))
        show = show.loc[mask].reset_index(drop=True)
        lines.append(show.to_markdown(index=False))
        lines.append("")

    lines.append("## Notes")
    lines.append("- If strict gates fail, main paper claims must be reframed to match strict evidence.")
    lines.append("- This report is the single source of truth for strict vs legacy audit status.")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_final_v4_strict(
    *,
    final_dir: Path,
    strict_phase9_out: Path,
    strict_phase13_out: Path,
    strict_phase22_out: Path,
    legacy_phase9_out: Path | None,
    legacy_phase13_out: Path | None,
    legacy_phase22_out: Path | None,
    strict_audit_report_md: Path,
    ab_table_csv: Path,
) -> Path:
    # Start from the camera-ready V3 bundle as a base, then overlay strict artifacts.
    src_base = ROOT / "outputs" / "final_v3"
    if not src_base.exists():
        raise FileNotFoundError(src_base)
    if final_dir.exists():
        shutil.rmtree(final_dir)
    shutil.copytree(src_base, final_dir)

    # Refresh paper/docs/reports (so strict audit files are included).
    for name in ("paper", "docs", "reports"):
        dst = final_dir / name
        if dst.exists():
            shutil.rmtree(dst)
        _copytree_overwrite(ROOT / name, dst)

    # Add strict outputs.
    for d in [strict_phase9_out, strict_phase13_out, strict_phase22_out]:
        _copytree_overwrite(d, final_dir / d.name)

    # Add diagnostic legacy outputs for appendix reproducibility (optional).
    if legacy_phase9_out is not None:
        diag_dir = final_dir / "diagnostics"
        diag_dir.mkdir(parents=True, exist_ok=True)
        for d in [legacy_phase9_out, legacy_phase13_out, legacy_phase22_out]:
            if d is None:
                continue
            _copytree_overwrite(d, diag_dir / d.name)

    # Build manifest.json.
    stats_map: dict[str, dict] = {}
    for key, p in {
        "phase9_strict": final_dir / strict_phase9_out.name / "stats.json",
        "phase13_strict": final_dir / strict_phase13_out.name / "stats.json",
        "phase22_strict": final_dir / strict_phase22_out.name / "stats.json",
        "phase9_legacy_diag": (final_dir / "diagnostics" / legacy_phase9_out.name / "stats.json") if legacy_phase9_out else None,
        "phase13_legacy_diag": (final_dir / "diagnostics" / legacy_phase13_out.name / "stats.json") if legacy_phase13_out else None,
        "phase22_legacy_diag": (final_dir / "diagnostics" / legacy_phase22_out.name / "stats.json") if legacy_phase22_out else None,
    }.items():
        if p is None or not p.exists():
            continue
        obj = _load_json(p)
        runtime_hours = float(obj.get("runtime_hours", 0.0))
        stats_map[key] = {
            "path": str(p.relative_to(final_dir)),
            "gate_check": obj.get("gate_check", {}),
            "runtime_hours": float(runtime_hours),
            "version": obj.get("version", ""),
        }

    key_rel_paths = [
        str(strict_audit_report_md),
        str(ab_table_csv),
        f"{strict_phase9_out.name}/stats.json",
        f"{strict_phase13_out.name}/stats.json",
        f"{strict_phase22_out.name}/stats.json",
        "docs/router_protocol_v1.md",
        "docs/neurips_method_v1.md",
    ]
    key_files: list[dict] = []
    for rel in key_rel_paths:
        rel_p = Path(rel)
        p = final_dir / rel_p
        if not p.exists() or p.is_dir():
            continue
        key_files.append({"path": str(rel_p), "sha256": _sha256(p)})

    manifest = {
        "bundle": str(final_dir),
        "created_at": time.strftime("%Y-%m-%d"),
        "stats": stats_map,
        "key_files": key_files,
    }
    out_manifest = final_dir / "manifest.json"
    out_manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return out_manifest


def main() -> None:
    args = parse_args()
    t0 = time.perf_counter()
    seeds = _parse_seeds(args.seeds)
    strict_tables = Path(args.strict_tables_dir)
    legacy_tables = Path(args.legacy_tables_dir)
    strict_tables.mkdir(parents=True, exist_ok=True)
    legacy_tables.mkdir(parents=True, exist_ok=True)

    # Strict run.
    strict_p9_report = Path("reports") / f"{Path(args.strict_phase9_out).name}.md"
    strict_p13_report = Path("reports") / f"{Path(args.strict_phase13_out).name}.md"
    strict_p22_report = Path("reports") / f"{Path(args.strict_phase22_out).name}.md"

    _run_phase9(
        variant="strict",
        out_dir=args.strict_phase9_out,
        report_md=strict_p9_report,
        tables_dir=strict_tables,
        seeds=args.seeds,
        device=args.device,
        checkpoint=args.checkpoint,
        benchmark_root=args.benchmark_root,
        dataset_root=args.dataset_root,
        reuse_common=args.reuse_common_dir,
        phase8_calib_split_mode="train_val",
        phase8_conformal_select_on="calib",
        phase8_probe_search_on="calib",
        phase8_strict_tune_violation_margin=float(args.strict_phase8_tune_violation_margin),
        phase8_strict_tune_ci_margin=float(args.strict_phase8_tune_ci_margin),
        phase8_probe_include_cost_feature=bool(args.strict_phase8_probe_include_cost_feature),
        phase8_probe_selection_mode=str(args.strict_phase8_probe_selection_mode),
        phase8_probe_lcb_alpha=float(args.strict_phase8_probe_lcb_alpha),
        force=bool(args.force),
    )
    _run_phase13(
        variant="strict",
        phase9_root=args.strict_phase9_out,
        out_dir=args.strict_phase13_out,
        report_md=strict_p13_report,
        tables_dir=strict_tables,
        external_baselines_csv=strict_tables / "table_phase9_external_baselines.csv",
        force=bool(args.force),
    )
    _run_phase22(
        variant="strict",
        phase9_root=args.strict_phase9_out,
        out_dir=args.strict_phase22_out,
        report_md=strict_p22_report,
        tables_dir=strict_tables,
        force=bool(args.force),
    )

    strict_stats = {
        "p9": _load_json(args.strict_phase9_out / "stats.json"),
        "p13": _load_json(args.strict_phase13_out / "stats.json"),
        "p22": _load_json(args.strict_phase22_out / "stats.json"),
    }

    legacy_stats = None
    ab_df = None
    if not bool(args.skip_legacy):
        legacy_p9_report = Path("reports") / f"{Path(args.legacy_phase9_out).name}.md"
        legacy_p13_report = Path("reports") / f"{Path(args.legacy_phase13_out).name}.md"
        legacy_p22_report = Path("reports") / f"{Path(args.legacy_phase22_out).name}.md"

        _run_phase9(
            variant="legacy_diag",
            out_dir=args.legacy_phase9_out,
            report_md=legacy_p9_report,
            tables_dir=legacy_tables,
            seeds=args.seeds,
            device=args.device,
            checkpoint=args.checkpoint,
            benchmark_root=args.benchmark_root,
            dataset_root=args.dataset_root,
            reuse_common=args.reuse_common_dir,
            phase8_calib_split_mode="none",
            phase8_conformal_select_on="test",
            phase8_probe_search_on="test",
            phase8_strict_tune_violation_margin=0.14,
            phase8_strict_tune_ci_margin=0.13,
            phase8_probe_include_cost_feature=False,
            phase8_probe_selection_mode="grid_search",
            phase8_probe_lcb_alpha=0.10,
            force=bool(args.force),
        )
        _run_phase13(
            variant="legacy_diag",
            phase9_root=args.legacy_phase9_out,
            out_dir=args.legacy_phase13_out,
            report_md=legacy_p13_report,
            tables_dir=legacy_tables,
            external_baselines_csv=legacy_tables / "table_phase9_external_baselines.csv",
            force=bool(args.force),
        )
        _run_phase22(
            variant="legacy_diag",
            phase9_root=args.legacy_phase9_out,
            out_dir=args.legacy_phase22_out,
            report_md=legacy_p22_report,
            tables_dir=legacy_tables,
            force=bool(args.force),
        )

        legacy_stats = {
            "p9": _load_json(args.legacy_phase9_out / "stats.json"),
            "p13": _load_json(args.legacy_phase13_out / "stats.json"),
            "p22": _load_json(args.legacy_phase22_out / "stats.json"),
        }
        ab_df = _ab_summary(strict=strict_stats, legacy=legacy_stats)
        args.ab_table_csv.parent.mkdir(parents=True, exist_ok=True)
        ab_df.to_csv(args.ab_table_csv, index=False)

    strict_gates = _strict_gate_summary(strict_stats["p9"], strict_stats["p13"], strict_stats["p22"])

    _write_strict_audit_report(
        path=args.strict_audit_report_md,
        strict=strict_stats,
        legacy=legacy_stats,
        ab_df=ab_df,
        strict_gates=strict_gates,
        strict_tables_dir=strict_tables,
        legacy_tables_dir=legacy_tables if legacy_stats is not None else None,
    )

    manifest = _build_final_v4_strict(
        final_dir=args.final_dir,
        strict_phase9_out=args.strict_phase9_out,
        strict_phase13_out=args.strict_phase13_out,
        strict_phase22_out=args.strict_phase22_out,
        legacy_phase9_out=None if legacy_stats is None else args.legacy_phase9_out,
        legacy_phase13_out=None if legacy_stats is None else args.legacy_phase13_out,
        legacy_phase22_out=None if legacy_stats is None else args.legacy_phase22_out,
        strict_audit_report_md=args.strict_audit_report_md,
        ab_table_csv=args.ab_table_csv if legacy_stats is not None else args.ab_table_csv,
    )

    runtime_h = float((time.perf_counter() - t0) / 3600.0)
    print(f"[phase27] done in {runtime_h:.3f} h; manifest={manifest}")
    if bool(args.enforce_gate):
        # Hard-gate only the strict no-test-tuning protocol check; performance gates are assessed in TASK.md.
        cfg = strict_stats["p9"].get("router_eval_config", {})
        no_test = (
            str(cfg.get("calib_split_mode", "")) == "train_val"
            and str(cfg.get("conformal_select_on", "")) == "calib"
            and str(cfg.get("probe_search_on", "")) == "calib"
        )
        if not bool(no_test):
            raise RuntimeError(f"[phase27] strict protocol violation: router_eval_config={cfg}")


if __name__ == "__main__":
    main()
