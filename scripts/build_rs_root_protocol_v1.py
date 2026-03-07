from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build frozen RS root protocol v1 manifest/report.")
    p.add_argument("--exp3-summary", type=Path, default=Path("outputs/paper/manual_v11b_exp3_full/exp_results_summary.csv"))
    p.add_argument("--exp4-fair-summary", type=Path, default=Path("outputs/paper/manual_v11b_exp4_fair/exp_results_summary.csv"))
    p.add_argument("--ordinary-summary", type=Path, default=Path("outputs/paper/manual_v11b_exp12/exp_results_summary.csv"))
    p.add_argument("--parasol-meta", type=Path, default=Path("data/benchmark/parasol_narrow/meta.json"))
    p.add_argument("--exp3-manifest", type=Path, default=Path("outputs/paper/exp3_final_manual_v11b_manifest.json"))
    p.add_argument("--out-manifest", type=Path, default=Path("outputs/rs_root_protocol_v1/manifest.json"))
    p.add_argument("--out-report", type=Path, default=Path("reports/rs_root_protocol_v1.md"))
    return p.parse_args()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _find_row(rows: list[dict[str, str]], experiment: str, dataset: str, method: str) -> dict[str, str]:
    for row in rows:
        if row.get("experiment") == experiment and row.get("dataset") == dataset and row.get("method") == method:
            return row
    raise KeyError((experiment, dataset, method))


def _to_float(row: dict[str, str], key: str) -> float:
    return float(row[key])


def _percent_delta(new: float, base: float) -> float:
    return 100.0 * (float(new) - float(base)) / max(abs(float(base)), 1e-12)


def main() -> None:
    args = parse_args()
    exp3_rows = _read_csv_rows(args.exp3_summary)
    exp4_rows = _read_csv_rows(args.exp4_fair_summary)
    ordinary_rows = _read_csv_rows(args.ordinary_summary)
    parasol_meta = json.loads(args.parasol_meta.read_text(encoding="utf-8"))
    exp3_manifest = json.loads(args.exp3_manifest.read_text(encoding="utf-8"))

    exp3_full = _find_row(exp3_rows, "exp3_ablation", "parasol", "Full")
    exp3_no_rs = _find_row(exp3_rows, "exp3_ablation", "parasol", "No-RS")
    exp3_no_res = _find_row(exp3_rows, "exp3_ablation", "parasol", "No-Residual")
    exp3_narrow_full = _find_row(exp3_rows, "exp3_ablation_scene", "parasol:narrow_passage", "Full")
    exp3_narrow_no_rs = _find_row(exp3_rows, "exp3_ablation_scene", "parasol:narrow_passage", "No-RS")

    exp4_hybrid = _find_row(exp4_rows, "exp4_public_kinodynamic", "parasol", "Hybrid A* (RS)")
    exp4_ours = _find_row(exp4_rows, "exp4_public_kinodynamic", "parasol", "Ours")
    exp4_bit = _find_row(exp4_rows, "exp4_public_kinodynamic", "parasol", "Kinodynamic BIT*")
    exp4_rrt = _find_row(exp4_rows, "exp4_public_kinodynamic", "parasol", "Kinodynamic RRT*")

    ordinary_mp_a = _find_row(ordinary_rows, "exp1_mp", "mp", "A*")
    ordinary_mp_ours = _find_row(ordinary_rows, "exp1_mp", "mp", "Ours")
    ordinary_mix_a = _find_row(ordinary_rows, "exp1_standard", "mp+csm", "A*")
    ordinary_mix_ours = _find_row(ordinary_rows, "exp1_standard", "mp+csm", "Ours")
    ordinary_csm_a = _find_row(ordinary_rows, "exp2_csm", "csm", "A*")
    ordinary_csm_ours = _find_row(ordinary_rows, "exp2_csm", "csm", "Ours")

    manifest: dict[str, Any] = {
        "version": "rs_root_protocol_v1",
        "status": "frozen-root-protocol",
        "primary_message": "Use this bundle only for the RS-cost-field root claim. Hybrid A* (RS) is the primary nearest baseline; BIT*/RRT* are auxiliary only.",
        "inputs": {
            str(args.exp3_summary): _sha256(args.exp3_summary),
            str(args.exp4_fair_summary): _sha256(args.exp4_fair_summary),
            str(args.ordinary_summary): _sha256(args.ordinary_summary),
            str(args.parasol_meta): _sha256(args.parasol_meta),
            str(args.exp3_manifest): _sha256(args.exp3_manifest),
        },
        "frozen_protocol": {
            "hard_bundle": {
                "dataset": "parasol_narrow/test",
                "num_samples": int(parasol_meta["splits"]["test"]["num_samples"]),
                "num_maps": int(parasol_meta["splits"]["test"]["num_maps"]),
                "scenario_histogram": parasol_meta["splits"]["test"]["scenario_histogram"],
                "primary_rows": {
                    "full": exp3_full,
                    "no_rs": exp3_no_rs,
                    "no_residual": exp3_no_res,
                    "narrow_full": exp3_narrow_full,
                    "narrow_no_rs": exp3_narrow_no_rs,
                },
                "derived": {
                    "success_drop_pp_overall": 100.0 * (_to_float(exp3_full, "success_rate") - _to_float(exp3_no_rs, "success_rate")),
                    "success_drop_pp_narrow": 100.0 * (_to_float(exp3_narrow_full, "success_rate") - _to_float(exp3_narrow_no_rs, "success_rate")),
                    "delta_expansions_full_vs_no_residual_percent": _percent_delta(_to_float(exp3_full, "avg_expansions"), _to_float(exp3_no_res, "avg_expansions")),
                    "delta_time_full_vs_no_residual_percent": _percent_delta(_to_float(exp3_full, "avg_time_ms"), _to_float(exp3_no_res, "avg_time_ms")),
                },
            },
            "fair_nearest_baseline": {
                "dataset": "parasol",
                "fairness": {
                    "hybrid_budget_cap": 0,
                    "sampling_max_iters": 300,
                    "primary_nearest_baseline": "Hybrid A* (RS)",
                    "auxiliary_baselines": ["Kinodynamic BIT*", "Kinodynamic RRT*"],
                    "allowed_primary_axes": ["success", "avg_expansions", "avg_time_ms"],
                },
                "primary_rows": {
                    "ours": exp4_ours,
                    "hybrid_a_star_rs": exp4_hybrid,
                    "kinodynamic_bit_star": exp4_bit,
                    "kinodynamic_rrt_star": exp4_rrt,
                },
                "derived": {
                    "delta_expansions_ours_vs_hybrid_percent": _percent_delta(_to_float(exp4_ours, "avg_expansions"), _to_float(exp4_hybrid, "avg_expansions")),
                    "delta_time_ours_vs_hybrid_percent": _percent_delta(_to_float(exp4_ours, "avg_time_ms"), _to_float(exp4_hybrid, "avg_time_ms")),
                    "delta_path_length_ours_vs_hybrid_percent": _percent_delta(_to_float(exp4_ours, "avg_path_length"), _to_float(exp4_hybrid, "avg_path_length")),
                    "delta_time_ours_vs_bit_percent": _percent_delta(_to_float(exp4_ours, "avg_time_ms"), _to_float(exp4_bit, "avg_time_ms")),
                    "delta_time_ours_vs_rrt_percent": _percent_delta(_to_float(exp4_ours, "avg_time_ms"), _to_float(exp4_rrt, "avg_time_ms")),
                },
            },
            "ordinary_support": {
                "status": "auxiliary_support_only",
                "rows": {
                    "mp_a_star": ordinary_mp_a,
                    "mp_ours": ordinary_mp_ours,
                    "mp_csm_a_star": ordinary_mix_a,
                    "mp_csm_ours": ordinary_mix_ours,
                    "csm_a_star": ordinary_csm_a,
                    "csm_ours": ordinary_csm_ours,
                },
                "derived": {
                    "delta_expansions_mp_percent": _percent_delta(_to_float(ordinary_mp_ours, "avg_expansions"), _to_float(ordinary_mp_a, "avg_expansions")),
                    "delta_expansions_mpcsm_percent": _percent_delta(_to_float(ordinary_mix_ours, "avg_expansions"), _to_float(ordinary_mix_a, "avg_expansions")),
                    "delta_expansions_csm_percent": _percent_delta(_to_float(ordinary_csm_ours, "avg_expansions"), _to_float(ordinary_csm_a, "avg_expansions")),
                    "delta_time_mpcsm_percent": _percent_delta(_to_float(ordinary_mix_ours, "avg_time_ms"), _to_float(ordinary_mix_a, "avg_time_ms")),
                },
            },
        },
        "reproduce_exp3_command": exp3_manifest.get("reproduce_exp3_command"),
        "allowed_root_claims": [
            "Removing the RS cost field causes a large solvability collapse on the hard parasol_narrow bundle.",
            "Under the frozen fair kinodynamic comparison, the RS-guided current model improves search effort/time over Hybrid A* (RS) while matching success.",
            "On ordinary mp/csm maps, expansions stay near A*; this is support evidence, not the main root claim.",
        ],
        "forbidden_root_claims": [
            "Do not use the older non-fair BIT*/RRT* timing comparison as the primary RS-root claim.",
            "Do not claim that the RS cost field alone is already a stable overall SOTA across all nearest baselines.",
            "Do not merge RS-only/root claims with upper-layer residual or router claims without explicitly separating them.",
        ],
    }

    lines = [
        "# RS Root Protocol V1",
        "",
        "Status: `frozen-root-protocol`",
        "",
        "This report freezes the **single fair protocol bundle** that is allowed to support the `RS cost field` root claim.",
        "",
        "## Primary Reading Rule",
        "- Primary nearest-baseline claim must use `outputs/paper/manual_v11b_exp4_fair/exp_results_summary.csv`.",
        "- `Hybrid A* (RS)` is the primary nearest baseline.",
        "- `Kinodynamic BIT* / RRT*` are auxiliary only and must not be used as the main root claim target.",
        "",
        "## Block A — Hard-Bundle Necessity (parasol_narrow/test)",
        f"- samples: `{manifest['frozen_protocol']['hard_bundle']['num_samples']}`; maps: `{manifest['frozen_protocol']['hard_bundle']['num_maps']}`",
        f"- overall success: `Full={_to_float(exp3_full, 'success_rate'):.6f}` vs `No-RS={_to_float(exp3_no_rs, 'success_rate'):.6f}`",
        f"- narrow_passage success: `Full={_to_float(exp3_narrow_full, 'success_rate'):.6f}` vs `No-RS={_to_float(exp3_narrow_no_rs, 'success_rate'):.6f}`",
        f"- Full vs No-Residual expansions: `{manifest['frozen_protocol']['hard_bundle']['derived']['delta_expansions_full_vs_no_residual_percent']:.3f}%`",
        f"- Full vs No-Residual time: `{manifest['frozen_protocol']['hard_bundle']['derived']['delta_time_full_vs_no_residual_percent']:.3f}%`",
        "- Interpretation: this block supports the **necessity / solvability** side of the RS root claim.",
        "",
        "## Block B — Fair Nearest-Baseline Comparison (parasol, exp4_public_kinodynamic)",
        "- frozen fairness: `hybrid_budget_cap=0`, `sampling_max_iters=300`",
        f"- success: `Ours={_to_float(exp4_ours, 'success_rate'):.6f}` vs `Hybrid A* (RS)={_to_float(exp4_hybrid, 'success_rate'):.6f}`",
        f"- expansions delta vs Hybrid A* (RS): `{manifest['frozen_protocol']['fair_nearest_baseline']['derived']['delta_expansions_ours_vs_hybrid_percent']:.3f}%`",
        f"- time delta vs Hybrid A* (RS): `{manifest['frozen_protocol']['fair_nearest_baseline']['derived']['delta_time_ours_vs_hybrid_percent']:.3f}%`",
        f"- path-length delta vs Hybrid A* (RS): `{manifest['frozen_protocol']['fair_nearest_baseline']['derived']['delta_path_length_ours_vs_hybrid_percent']:.3f}%`",
        f"- time delta vs Kinodynamic BIT*: `{manifest['frozen_protocol']['fair_nearest_baseline']['derived']['delta_time_ours_vs_bit_percent']:.3f}%`",
        f"- time delta vs Kinodynamic RRT*: `{manifest['frozen_protocol']['fair_nearest_baseline']['derived']['delta_time_ours_vs_rrt_percent']:.3f}%`",
        "- Interpretation: only the comparison to `Hybrid A* (RS)` is allowed to support the **primary nearest-baseline** RS-root claim.",
        "",
        "## Block C — Ordinary-Scene Support (auxiliary only)",
        f"- mp expansions delta vs A*: `{manifest['frozen_protocol']['ordinary_support']['derived']['delta_expansions_mp_percent']:.3f}%`",
        f"- mp+csm expansions delta vs A*: `{manifest['frozen_protocol']['ordinary_support']['derived']['delta_expansions_mpcsm_percent']:.3f}%`",
        f"- csm expansions delta vs A*: `{manifest['frozen_protocol']['ordinary_support']['derived']['delta_expansions_csm_percent']:.3f}%`",
        f"- mp+csm time delta vs A*: `{manifest['frozen_protocol']['ordinary_support']['derived']['delta_time_mpcsm_percent']:.3f}%`",
        "- Interpretation: this block may support a limited statement like 'expansions stay near A* on ordinary maps', but it is **not** the main root claim.",
        "",
        "## Allowed Root Claims",
    ]
    for item in manifest["allowed_root_claims"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Forbidden Root Claims"])
    for item in manifest["forbidden_root_claims"]:
        lines.append(f"- {item}")
    lines.extend([
        "",
        "## Artifact Chain",
        f"- manifest: `{args.out_manifest}`",
        f"- report: `{args.out_report}`",
        f"- exp3 source: `{args.exp3_summary}`",
        f"- exp4 fair source: `{args.exp4_fair_summary}`",
        f"- ordinary support source: `{args.ordinary_summary}`",
        f"- parasol meta: `{args.parasol_meta}`",
    ])

    args.out_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.out_report.parent.mkdir(parents=True, exist_ok=True)
    args.out_manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    args.out_report.write_text("\n".join(lines), encoding="utf-8")
    print(f"[rs-root] manifest={args.out_manifest}")
    print(f"[rs-root] report={args.out_report}")


if __name__ == "__main__":
    main()
