from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.artifact_hash import sha256_file
from utils.parquet_guard import compare_record, mismatch_summary


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Repo-level validity scan: recompute key metrics from artifacts, check split overlap, and detect output drift."
    )
    p.add_argument("--strict-bundle", type=Path, default=Path("outputs/final_v5_strict"))
    p.add_argument("--legacy-bundle", type=Path, default=Path("outputs/final_v2"))
    p.add_argument("--out-md", type=Path, default=Path("reports/router_validity_audit_v3_fullscan.md"))
    p.add_argument("--check-workspace-drift", action=argparse.BooleanOptionalAction, default=True)
    return p.parse_args()


def _load_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _safe_read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(Path(path))


def _split_overlap(dataset_root: Path) -> dict[str, object]:
    out: dict[str, object] = {"dataset_root": str(dataset_root)}
    splits: dict[str, set[str]] = {}
    for split in ("train", "calib", "test"):
        p = Path(dataset_root) / f"{split}_index.csv"
        df = _safe_read_csv(p)
        key = "source_path" if "source_path" in df.columns else "sample_name"
        splits[split] = set(df[key].astype(str).tolist())
    pairs = [("train", "calib"), ("train", "test"), ("calib", "test")]
    overlaps: dict[str, int] = {}
    for a, b in pairs:
        overlaps[f"{a}_x_{b}"] = int(len(splits[a] & splits[b]))
    out["overlap_counts"] = overlaps
    out["pass"] = bool(all(v == 0 for v in overlaps.values()))
    return out


def _manifest_phase_dirs(bundle: Path) -> dict[str, Path]:
    man = _load_json(Path(bundle) / "manifest.json")
    stats = man.get("stats", {})
    out: dict[str, Path] = {}
    for k, v in stats.items():
        p = Path(v.get("path", ""))
        if not p.name:
            continue
        out[str(k)] = Path(p).parent
    return out


def _eval_J(
    *,
    df: pd.DataFrame,
    use_fast: np.ndarray,
    t_ref: float,
    beta: float,
    extra_time_ms: np.ndarray | None,
) -> tuple[np.ndarray, float]:
    q = df["q_rel"].to_numpy(dtype=np.float64)
    j_fast = df["T_fast_ms"].to_numpy(dtype=np.float64) / max(float(t_ref), 1e-9) + float(beta) * np.maximum(q, 0.0)
    j_slow = df["T_slow_ms"].to_numpy(dtype=np.float64) / max(float(t_ref), 1e-9)
    ji = np.where(use_fast.astype(bool), j_fast, j_slow).astype(np.float64)
    if extra_time_ms is not None:
        ji = ji + np.asarray(extra_time_ms, dtype=np.float64) / max(float(t_ref), 1e-9)
    return ji, float(np.mean(ji))


def _phase9_recompute(bundle: Path, phase9_dir: Path, *, include_probe_runtime: bool) -> dict[str, object]:
    root = Path(bundle) / phase9_dir
    stats = _load_json(root / "stats.json")
    seeds = [int(s) for s in stats.get("seeds", [])]
    cf_test = pd.read_parquet(root / "common" / "router_counterfactual_test.parquet")
    probe = pd.read_parquet(root / "router_eval" / "common" / "probe_features_test.parquet")[["sample_name", "probe_runtime_ms"]]

    pooled: list[np.ndarray] = []
    for seed in seeds:
        seed_root = root / "router_eval" / "seeds" / f"seed_{seed}" / "mixed"
        p5 = pd.read_parquet(seed_root / "conformal_strict_v2" / "test_decisions.parquet")[["sample_name", "use_fast"]].rename(
            columns={"use_fast": "use_fast_p5"}
        )
        p6 = pd.read_parquet(seed_root / "probe_strict_v2" / "test_decisions.parquet")[["sample_name", "use_fast"]].rename(
            columns={"use_fast": "use_fast_router"}
        )
        m_probe = _load_json(seed_root / "probe_strict_v2" / "policy_metrics.json")
        t_ref = float(m_probe["objective"]["T_ref"])
        beta = float(m_probe["objective"]["beta"])

        df = cf_test.merge(p5, on="sample_name", how="inner").merge(p6, on="sample_name", how="inner").merge(probe, on="sample_name", how="left")
        if len(df) != len(cf_test):
            raise RuntimeError(f"Phase9 merge mismatch (seed={seed}): {len(df)} != {len(cf_test)}")

        extra = df["probe_runtime_ms"].to_numpy(dtype=np.float64) if bool(include_probe_runtime) else None
        j_p5_i, _j_p5 = _eval_J(df=df, use_fast=df["use_fast_p5"].to_numpy(dtype=bool), t_ref=t_ref, beta=beta, extra_time_ms=None)
        j_r_i, _j_r = _eval_J(
            df=df, use_fast=df["use_fast_router"].to_numpy(dtype=bool), t_ref=t_ref, beta=beta, extra_time_ms=extra
        )
        pooled.append((j_p5_i - j_r_i).astype(np.float64))

    pooled_arr = np.concatenate(pooled) if pooled else np.zeros(0, dtype=np.float64)
    mean = float(np.mean(pooled_arr)) if pooled_arr.size else float("nan")
    std = float(np.std(pooled_arr)) if pooled_arr.size else float("nan")
    want = float(stats["pooled"]["mean_delta_j"])
    want_std = float(stats["pooled"]["std_delta_j"])
    return {
        "phase9_dir": str(phase9_dir),
        "include_probe_runtime": bool(include_probe_runtime),
        "n": int(pooled_arr.size),
        "mean_delta_j_recomputed": mean,
        "std_delta_j_recomputed": std,
        "mean_delta_j_stats": want,
        "std_delta_j_stats": want_std,
        "absdiff_mean": float(abs(mean - want)),
        "absdiff_std": float(abs(std - want_std)),
        "pass_exact": bool(abs(mean - want) <= 1e-12 and abs(std - want_std) <= 1e-12),
    }


def _phase13_recompute(bundle: Path, phase9_dir: Path, phase13_dir: Path, *, include_probe_runtime: bool) -> dict[str, object]:
    p9 = Path(bundle) / phase9_dir
    p13 = Path(bundle) / phase13_dir
    stats = _load_json(p13 / "stats.json")
    seeds = [int(s) for s in stats.get("seeds", [])]

    test_df = pd.read_parquet(p9 / "common" / "router_counterfactual_test.parquet")
    probe = pd.read_parquet(p9 / "router_eval" / "common" / "probe_features_test.parquet")[["sample_name", "probe_runtime_ms"]]
    base = test_df.merge(probe, on="sample_name", how="left")

    seed_improves: list[float] = []
    pooled: list[np.ndarray] = []
    for seed in seeds:
        seed_root = p9 / "router_eval" / "seeds" / f"seed_{seed}" / "mixed"
        ours_dec = pd.read_parquet(seed_root / "probe_strict_v2" / "test_decisions.parquet")[["sample_name", "use_fast"]].rename(
            columns={"use_fast": "use_fast_ours"}
        )
        p5_dec = pd.read_parquet(seed_root / "conformal_strict_v2" / "test_decisions.parquet")[
            ["sample_name", "use_fast"]
        ].rename(columns={"use_fast": "use_fast_p5"})
        m_probe = _load_json(seed_root / "probe_strict_v2" / "policy_metrics.json")
        t_ref = float(m_probe["objective"]["T_ref"])
        beta = float(m_probe["objective"]["beta"])

        df = base.merge(ours_dec, on="sample_name", how="inner").merge(p5_dec, on="sample_name", how="inner")
        extra = df["probe_runtime_ms"].to_numpy(dtype=np.float64) if bool(include_probe_runtime) else None
        j_ours_i, j_ours = _eval_J(df=df, use_fast=df["use_fast_ours"].to_numpy(dtype=bool), t_ref=t_ref, beta=beta, extra_time_ms=extra)
        j_p5_i, j_p5 = _eval_J(df=df, use_fast=df["use_fast_p5"].to_numpy(dtype=bool), t_ref=t_ref, beta=beta, extra_time_ms=None)

        imp = float((j_p5 - j_ours) / max(abs(j_p5), 1e-12))
        seed_improves.append(imp)
        pooled.append(((j_p5_i - j_ours_i) / max(abs(j_p5), 1e-9)).astype(np.float64))

    mean_imp = float(np.mean(seed_improves)) if seed_improves else float("nan")
    pooled_arr = np.concatenate(pooled) if pooled else np.zeros(0, dtype=np.float64)
    pooled_mean = float(np.mean(pooled_arr)) if pooled_arr.size else float("nan")

    want_mean = float(stats["summary"]["j_improve_vs_strongest_baseline_mean"])
    want_pooled = float(stats["summary"]["pooled_delta_j_mean"])
    return {
        "phase13_dir": str(phase13_dir),
        "phase9_dir": str(phase9_dir),
        "include_probe_runtime": bool(include_probe_runtime),
        "seed_mean_recomputed": mean_imp,
        "seed_mean_stats": want_mean,
        "pooled_mean_recomputed": pooled_mean,
        "pooled_mean_stats": want_pooled,
        "absdiff_seed_mean": float(abs(mean_imp - want_mean)),
        "absdiff_pooled_mean": float(abs(pooled_mean - want_pooled)),
        "pass_close": bool(abs(mean_imp - want_mean) <= 1e-10 and abs(pooled_mean - want_pooled) <= 1e-10),
    }


def _phase22_recompute(bundle: Path, phase9_dir: Path, phase22_dir: Path, *, include_probe_runtime: bool) -> dict[str, object]:
    p9 = Path(bundle) / phase9_dir
    p22 = Path(bundle) / phase22_dir
    stats = _load_json(p22 / "stats.json")
    seeds = [int(s) for s in stats.get("seeds", [])]
    best_direct = str(stats.get("best_direct_baseline", ""))
    if not best_direct:
        raise RuntimeError("Missing best_direct_baseline in Phase22 stats.")

    test_df = pd.read_parquet(p9 / "common" / "router_counterfactual_test.parquet")
    probe = pd.read_parquet(p9 / "router_eval" / "common" / "probe_features_test.parquet")[["sample_name", "probe_runtime_ms"]]
    base = test_df.merge(probe, on="sample_name", how="left")

    seed_improves: list[float] = []
    pooled: list[np.ndarray] = []
    seed_improves_bd_vs_p5: list[float] = []
    pooled_bd_vs_p5: list[np.ndarray] = []

    for seed in seeds:
        seed_root = p9 / "router_eval" / "seeds" / f"seed_{seed}" / "mixed"
        ours_dec = pd.read_parquet(seed_root / "probe_strict_v2" / "test_decisions.parquet")[["sample_name", "use_fast"]].rename(
            columns={"use_fast": "use_fast_ours"}
        )
        p5_dec = pd.read_parquet(seed_root / "conformal_strict_v2" / "test_decisions.parquet")[
            ["sample_name", "use_fast"]
        ].rename(columns={"use_fast": "use_fast_p5"})
        m_probe = _load_json(seed_root / "probe_strict_v2" / "policy_metrics.json")
        t_ref = float(m_probe["objective"]["T_ref"])
        beta = float(m_probe["objective"]["beta"])

        base_dec = pd.read_parquet(p22 / "seeds" / f"seed_{seed}" / best_direct / "test_decisions.parquet")[
            ["sample_name", "use_fast"]
        ].rename(columns={"use_fast": "use_fast_base"})

        df = base.merge(ours_dec, on="sample_name", how="inner").merge(p5_dec, on="sample_name", how="inner").merge(base_dec, on="sample_name", how="inner")

        extra = df["probe_runtime_ms"].to_numpy(dtype=np.float64) if bool(include_probe_runtime) else None
        j_ours_i, j_ours = _eval_J(df=df, use_fast=df["use_fast_ours"].to_numpy(dtype=bool), t_ref=t_ref, beta=beta, extra_time_ms=extra)
        j_base_i, j_base = _eval_J(df=df, use_fast=df["use_fast_base"].to_numpy(dtype=bool), t_ref=t_ref, beta=beta, extra_time_ms=None)
        j_p5_i, j_p5 = _eval_J(df=df, use_fast=df["use_fast_p5"].to_numpy(dtype=bool), t_ref=t_ref, beta=beta, extra_time_ms=None)

        imp = float((j_base - j_ours) / max(abs(j_base), 1e-12))
        seed_improves.append(imp)
        pooled.append(((j_base_i - j_ours_i) / max(abs(j_base), 1e-9)).astype(np.float64))

        imp_bd = float((j_p5 - j_base) / max(abs(j_p5), 1e-12))
        seed_improves_bd_vs_p5.append(imp_bd)
        pooled_bd_vs_p5.append(((j_p5_i - j_base_i) / max(abs(j_p5), 1e-9)).astype(np.float64))

    mean_imp = float(np.mean(seed_improves)) if seed_improves else float("nan")
    pooled_arr = np.concatenate(pooled) if pooled else np.zeros(0, dtype=np.float64)
    pooled_mean = float(np.mean(pooled_arr)) if pooled_arr.size else float("nan")

    mean_bd = float(np.mean(seed_improves_bd_vs_p5)) if seed_improves_bd_vs_p5 else float("nan")
    pooled_bd_arr = np.concatenate(pooled_bd_vs_p5) if pooled_bd_vs_p5 else np.zeros(0, dtype=np.float64)
    pooled_bd_mean = float(np.mean(pooled_bd_arr)) if pooled_bd_arr.size else float("nan")

    want_pct = float(stats["summary"]["j_improve_vs_best_direct_mean"])
    want_pooled = float(stats["summary"]["pooled_delta_j_mean"])
    want_bd_pct = float(stats["summary"]["j_improve_best_direct_vs_p5_mean"])
    want_bd_pooled_ci_lo = float(stats["summary"]["pooled_delta_j_best_direct_vs_p5_ci95"][0])
    want_bd_pooled_ci_hi = float(stats["summary"]["pooled_delta_j_best_direct_vs_p5_ci95"][1])

    # Note: Phase22 stores j_improve_vs_best_direct_mean in percent.
    mean_pct = mean_imp * 100.0
    mean_bd_pct = mean_bd * 100.0
    return {
        "phase22_dir": str(phase22_dir),
        "phase9_dir": str(phase9_dir),
        "include_probe_runtime": bool(include_probe_runtime),
        "best_direct_baseline": best_direct,
        "mean_pct_recomputed": float(mean_pct),
        "mean_pct_stats": want_pct,
        "pooled_mean_recomputed": pooled_mean,
        "pooled_mean_stats": want_pooled,
        "absdiff_mean_pct": float(abs(mean_pct - want_pct)),
        "absdiff_pooled_mean": float(abs(pooled_mean - want_pooled)),
        "best_direct_vs_p5_mean_pct_recomputed": float(mean_bd_pct),
        "best_direct_vs_p5_mean_pct_stats": want_bd_pct,
        "best_direct_vs_p5_pooled_mean_recomputed": float(pooled_bd_mean),
        "best_direct_vs_p5_pooled_ci95_stats": [want_bd_pooled_ci_lo, want_bd_pooled_ci_hi],
        "pass_close": bool(abs(mean_pct - want_pct) <= 1e-8 and abs(pooled_mean - want_pooled) <= 1e-10),
    }


def _sha256_binding_ok(path: Path) -> tuple[bool, str]:
    rec = Path(path)
    if not rec.exists():
        return False, "missing_record"
    obj = json.loads(rec.read_text(encoding="utf-8"))
    paths = {k: Path(v) for k, v in obj.get("paths", {}).items()}
    ok, cur, prev = compare_record(rec, paths)
    return bool(ok), str(mismatch_summary(cur, prev))


def _workspace_drift_check(legacy_bundle: Path) -> dict[str, object]:
    # Detect common failure mode: someone overwrote `outputs/*` after bundling,
    # making the workspace directory inconsistent with the frozen bundle copy.
    out: dict[str, object] = {"checked": True, "mismatches": []}
    legacy_manifest = _load_json(Path(legacy_bundle) / "manifest.json")
    phase9_stats_path = Path(legacy_manifest["stats"]["phase9"]["path"])
    phase9_dir = phase9_stats_path.parent
    frozen_pq = Path(legacy_bundle) / phase9_dir / "common" / "router_counterfactual_test.parquet"

    live_pq = Path("outputs") / phase9_dir / "common" / "router_counterfactual_test.parquet"
    if frozen_pq.exists() and live_pq.exists():
        hf = sha256_file(frozen_pq)
        hl = sha256_file(live_pq)
        if hf != hl:
            out["mismatches"].append(
                {
                    "path": str(live_pq),
                    "frozen_bundle_path": str(frozen_pq),
                    "sha256_live": hl,
                    "sha256_frozen": hf,
                    "note": "Workspace output drift: live parquet differs from frozen bundle copy.",
                }
            )
    return out


def main() -> None:
    args = parse_args()
    strict_bundle = Path(args.strict_bundle)
    legacy_bundle = Path(args.legacy_bundle)

    strict_dirs = _manifest_phase_dirs(strict_bundle)
    legacy_dirs = _manifest_phase_dirs(legacy_bundle)

    # Phase dir names from manifests.
    strict_phase9 = strict_dirs.get("phase9_strict")
    strict_phase13 = strict_dirs.get("phase13_strict")
    strict_phase22 = strict_dirs.get("phase22_strict")
    legacy_phase9 = legacy_dirs.get("phase9")
    legacy_phase13 = legacy_dirs.get("phase13")
    legacy_phase22 = legacy_dirs.get("phase22") if "phase22" in legacy_dirs else legacy_dirs.get("phase22_strict")

    lines: list[str] = []
    lines.append("# Router Validity Audit (V3) — Fullscan")
    lines.append("")
    lines.append(f"- Date: `{pd.Timestamp.now().strftime('%Y-%m-%d')}`")
    lines.append(f"- Strict bundle: `{strict_bundle}`")
    lines.append(f"- Legacy bundle: `{legacy_bundle}`")
    lines.append("")

    # Split overlap.
    lines.append("## 1) Dataset split leakage (overlap) checks")
    for ds in [Path("data/router_phase9_public_v1"), Path("data/router_mixed_v1")]:
        res = _split_overlap(ds)
        lines.append(f"- `{ds}` pass: `{res['pass']}` overlap: `{res['overlap_counts']}`")
    lines.append("")

    # Phase9 recomputation: strict expects probe-in-T; legacy expects route-only.
    lines.append("## 2) Metrics reproducibility from artifacts (not hand-written)")
    if legacy_phase9 is not None:
        legacy_r = _phase9_recompute(legacy_bundle, legacy_phase9, include_probe_runtime=False)
        lines.append(f"- Legacy Phase9 (route-only) exact-match: `{legacy_r['pass_exact']}` absdiff_mean={legacy_r['absdiff_mean']:.3e}")
    if strict_phase9 is not None:
        strict_r = _phase9_recompute(strict_bundle, strict_phase9, include_probe_runtime=True)
        lines.append(f"- Strict Phase9 (probe-in-T) exact-match: `{strict_r['pass_exact']}` absdiff_mean={strict_r['absdiff_mean']:.3e}")
    lines.append("")

    if legacy_phase9 is not None and legacy_phase13 is not None:
        legacy13 = _phase13_recompute(legacy_bundle, legacy_phase9, legacy_phase13, include_probe_runtime=False)
        lines.append(
            f"- Legacy Phase13 (probe ignored in J) close-match: `{legacy13['pass_close']}` absdiff_seed_mean={legacy13['absdiff_seed_mean']:.3e}"
        )
    if strict_phase9 is not None and strict_phase13 is not None:
        strict13 = _phase13_recompute(strict_bundle, strict_phase9, strict_phase13, include_probe_runtime=True)
        lines.append(
            f"- Strict Phase13 (probe-in-T) close-match: `{strict13['pass_close']}` absdiff_seed_mean={strict13['absdiff_seed_mean']:.3e}"
        )
    lines.append("")

    if legacy_phase9 is not None and legacy_phase22 is not None:
        legacy22 = _phase22_recompute(legacy_bundle, legacy_phase9, legacy_phase22, include_probe_runtime=False)
        lines.append(f"- Legacy Phase22 close-match: `{legacy22['pass_close']}` absdiff_mean_pct={legacy22['absdiff_mean_pct']:.3e}")
    if strict_phase9 is not None and strict_phase22 is not None:
        strict22 = _phase22_recompute(strict_bundle, strict_phase9, strict_phase22, include_probe_runtime=True)
        lines.append(f"- Strict Phase22 close-match: `{strict22['pass_close']}` absdiff_mean_pct={strict22['absdiff_mean_pct']:.3e}")
    lines.append("")

    # SHA256 binding: strict chain only (legacy bundles predate full coverage).
    lines.append("## 3) Parquet SHA256 binding (overwrite detection)")
    strict_sha_checks: list[tuple[str, Path]] = []
    if strict_phase9 is not None:
        strict_sha_checks.append(("phase9/common/risk", strict_bundle / strict_phase9 / "common" / "risk" / "inputs_parquet_sha256.json"))
        strict_sha_checks.append(("phase9/router_eval", strict_bundle / strict_phase9 / "router_eval" / "inputs_parquet_sha256.json"))
    if strict_phase13 is not None:
        strict_sha_checks.append(("phase13", strict_bundle / strict_phase13 / "inputs_parquet_sha256.json"))
    if strict_phase22 is not None:
        strict_sha_checks.append(("phase22", strict_bundle / strict_phase22 / "inputs_parquet_sha256.json"))
    for name, rec in strict_sha_checks:
        ok, msg = _sha256_binding_ok(rec)
        lines.append(f"- Strict `{name}` sha256 record ok: `{ok}` ({msg})")
    lines.append("")

    # Workspace drift check (optional).
    if bool(args.check_workspace_drift):
        drift = _workspace_drift_check(legacy_bundle)
        lines.append("## 4) Workspace drift (bundle vs live outputs)")
        mism = drift.get("mismatches", [])
        if not mism:
            lines.append("- No drift detected for the sampled Phase9 parquet.")
        else:
            lines.append(f"- Drift detected: `{len(mism)}` mismatches.")
            for r in mism:
                lines.append(f"  - `{r['path']}` sha256_live=`{r['sha256_live'][:10]}` sha256_frozen=`{r['sha256_frozen'][:10]}`")
        lines.append("")

    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[audit_v3] wrote {args.out_md}")


if __name__ == "__main__":
    main()

