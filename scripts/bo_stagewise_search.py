from __future__ import annotations

import argparse
import csv
import json
import math
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from scipy.stats import norm
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Params:
    alpha_shallow: float
    alpha_deep: float
    alpha_decoder: float
    alpha_head: float
    residual_alpha: float

    def rounded_key(self, ndigits: int = 4) -> tuple[float, float, float, float, float]:
        return (
            round(float(self.alpha_shallow), ndigits),
            round(float(self.alpha_deep), ndigits),
            round(float(self.alpha_decoder), ndigits),
            round(float(self.alpha_head), ndigits),
            round(float(self.residual_alpha), ndigits),
        )

    def to_array(self) -> np.ndarray:
        return np.array(
            [
                float(self.alpha_shallow),
                float(self.alpha_deep),
                float(self.alpha_decoder),
                float(self.alpha_head),
                float(self.residual_alpha),
            ],
            dtype=np.float64,
        )


@dataclass
class EvalResult:
    split: str
    params: Params
    paper_out: str
    checkpoint: str
    success_full: float
    success_nores: float
    dE_percent: float
    dT_percent: float
    full_expansions: float
    nores_expansions: float
    full_time_ms: float
    nores_time_ms: float
    dE_narrow_percent: float
    dE_maze_percent: float
    dE_other_percent: float
    objective: float
    source: str


@dataclass(frozen=True)
class ObjectiveConfig:
    scene_penalty_narrow: float = 0.0
    scene_penalty_maze: float = 0.0
    scene_tol_narrow: float = 0.0
    scene_tol_maze: float = 0.0
    time_penalty_threshold: float = 10.0
    time_penalty_weight: float = 0.05


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Bayesian search on stage-wise interpolation + residual_alpha.")
    p.add_argument(
        "--ckpt-old",
        type=Path,
        default=Path("outputs/residual_fix_v3_train/checkpoints/heuristic_net_residual_fix_v3_train.pt"),
    )
    p.add_argument(
        "--ckpt-new",
        type=Path,
        default=Path("outputs/residual_structrank_distill_v2/checkpoints/heuristic_net_residual_structrank_distill_v2.pt"),
    )
    p.add_argument("--search-name", type=str, default="bo_stagewise_v1")
    p.add_argument("--device", type=str, default="cpu")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--n-bo-trials", type=int, default=6, help="Number of new quick trials to run.")
    p.add_argument("--candidate-pool", type=int, default=2000, help="Random candidate pool per BO step.")
    p.add_argument("--topk-full", type=int, default=2, help="Promote top-k quick candidates to Exp3 full.")
    p.add_argument("--warm-start", action="store_true", default=True, help="Load existing quick observations.")
    p.add_argument("--no-warm-start", action="store_true", help="Disable warm start.")

    # Search bounds (narrowed around current best region).
    p.add_argument("--bound-shallow-min", type=float, default=0.0)
    p.add_argument("--bound-shallow-max", type=float, default=0.08)
    p.add_argument("--bound-deep-min", type=float, default=0.45)
    p.add_argument("--bound-deep-max", type=float, default=0.75)
    p.add_argument("--bound-decoder-min", type=float, default=0.22)
    p.add_argument("--bound-decoder-max", type=float, default=0.42)
    p.add_argument("--bound-head-min", type=float, default=0.10)
    p.add_argument("--bound-head-max", type=float, default=0.26)
    p.add_argument("--bound-residual-min", type=float, default=0.62)
    p.add_argument("--bound-residual-max", type=float, default=0.82)
    p.add_argument("--xi", type=float, default=0.01, help="EI exploration parameter.")
    p.add_argument("--bn-stat-source", type=str, default="blend", choices=("blend", "old", "new"))
    p.add_argument("--max-full-candidates", type=int, default=3, help="Safety cap for full evaluations.")
    p.add_argument(
        "--scene-penalty-narrow",
        type=float,
        default=0.0,
        help="Penalty weight for positive dE in parasol:narrow_passage.",
    )
    p.add_argument(
        "--scene-penalty-maze",
        type=float,
        default=0.0,
        help="Penalty weight for positive dE in parasol:maze.",
    )
    p.add_argument(
        "--scene-tol-narrow",
        type=float,
        default=0.0,
        help="Allowed positive narrow dE before penalty starts.",
    )
    p.add_argument(
        "--scene-tol-maze",
        type=float,
        default=0.0,
        help="Allowed positive maze dE before penalty starts.",
    )
    p.add_argument("--time-penalty-threshold", type=float, default=10.0)
    p.add_argument("--time-penalty-weight", type=float, default=0.05)
    p.add_argument(
        "--bo-split",
        type=str,
        default="quick",
        choices=("quick", "full"),
        help="Optimization split. quick: BO on 8-case then promote; full: BO directly on 18-case.",
    )
    return p.parse_args()


def _run(cmd: list[str]) -> None:
    print("[cmd]", " ".join(cmd), flush=True)
    env = os.environ.copy()
    env.setdefault("MKL_THREADING_LAYER", "GNU")
    env.setdefault("OMP_NUM_THREADS", "1")
    subprocess.run(cmd, check=True, cwd=ROOT, env=env)


def _parse_exp3_metrics(summary_csv: Path) -> dict[str, float]:
    rows = list(csv.DictReader(summary_csv.open("r", encoding="utf-8")))
    full = next(r for r in rows if r["experiment"] == "exp3_ablation" and r["method"] == "Full")
    nores = next(r for r in rows if r["experiment"] == "exp3_ablation" and r["method"] == "No-Residual")

    def _to_float(v: str) -> float:
        try:
            return float(v)
        except Exception:
            return float("nan")

    def _safe_pct(a: float, b: float) -> float:
        if not math.isfinite(a) or not math.isfinite(b) or b <= 1e-9:
            return 0.0
        return (a - b) / b * 100.0

    def _scene_de(scene: str) -> float:
        try:
            fs = next(r for r in rows if r["experiment"] == "exp3_ablation_scene" and r["dataset"] == scene and r["method"] == "Full")
            ns = next(r for r in rows if r["experiment"] == "exp3_ablation_scene" and r["dataset"] == scene and r["method"] == "No-Residual")
        except StopIteration:
            return 0.0
        return _safe_pct(_to_float(fs["avg_expansions"]), _to_float(ns["avg_expansions"]))

    full_e = _to_float(full["avg_expansions"])
    nores_e = _to_float(nores["avg_expansions"])
    full_t = _to_float(full["avg_time_ms"])
    nores_t = _to_float(nores["avg_time_ms"])
    d_e = _safe_pct(full_e, nores_e)
    d_t = _safe_pct(full_t, nores_t)
    d_narrow = _scene_de("parasol:narrow_passage")
    d_maze = _scene_de("parasol:maze")
    d_other = _scene_de("parasol:other")
    return {
        "success_full": float(full["success_rate"]),
        "success_nores": float(nores["success_rate"]),
        "dE_percent": d_e,
        "dT_percent": d_t,
        "dE_narrow_percent": d_narrow,
        "dE_maze_percent": d_maze,
        "dE_other_percent": d_other,
        "full_expansions": full_e,
        "nores_expansions": nores_e,
        "full_time_ms": full_t,
        "nores_time_ms": nores_t,
    }


def _objective(
    success_full: float,
    success_nores: float,
    dE_percent: float,
    dT_percent: float,
    dE_narrow_percent: float,
    dE_maze_percent: float,
    cfg: ObjectiveConfig,
) -> float:
    # Minimize objective. Primary target: expansions gain, with strict success guard.
    obj = float(dE_percent)
    if success_full + 1e-9 < success_nores:
        obj += 1000.0 * (success_nores - success_full)
    # Mild penalty when timing regresses too much.
    if dT_percent > float(cfg.time_penalty_threshold):
        obj += float(cfg.time_penalty_weight) * (dT_percent - float(cfg.time_penalty_threshold))
    # Scene-structure penalties: discourage regressions in narrow/maze.
    obj += float(cfg.scene_penalty_narrow) * max(0.0, float(dE_narrow_percent) - float(cfg.scene_tol_narrow))
    obj += float(cfg.scene_penalty_maze) * max(0.0, float(dE_maze_percent) - float(cfg.scene_tol_maze))
    return obj


def _eval_trial(
    trial_id: str,
    split: str,
    params: Params,
    ckpt_old: Path,
    ckpt_new: Path,
    bn_stat_source: str,
    device: str,
    search_name: str,
    base_quick: bool,
    obj_cfg: ObjectiveConfig,
) -> EvalResult:
    ckpt_dir = ROOT / "outputs" / "checkpoints" / search_name
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = ckpt_dir / f"{trial_id}_{split}.pt"

    interp_cmd = [
        sys.executable,
        "scripts/interpolate_checkpoints_stagewise.py",
        "--ckpt-old",
        str(ckpt_old),
        "--ckpt-new",
        str(ckpt_new),
        "--out",
        str(ckpt_path),
        "--alpha-default",
        "0.0",
        "--alpha-shallow",
        f"{params.alpha_shallow:.6f}",
        "--alpha-deep",
        f"{params.alpha_deep:.6f}",
        "--alpha-decoder",
        f"{params.alpha_decoder:.6f}",
        "--alpha-head",
        f"{params.alpha_head:.6f}",
        "--bn-stat-source",
        bn_stat_source,
    ]
    _run(interp_cmd)

    out_dir = ROOT / "outputs" / "paper" / f"{search_name}_{split}_{trial_id}"
    common_args = [
        sys.executable,
        "scripts/evaluate_baselines.py",
        "--benchmark-root",
        "data/benchmark",
        "--hard-root",
        "data/benchmark/parasol_narrow/test",
        "--parasol-root",
        "data/benchmark/parasol_narrow/test",
        "--paper-out",
        str(out_dir),
        "--experiments",
        "exp3",
        "--ours-checkpoint",
        str(ckpt_path),
        "--device",
        str(device),
        "--seed",
        "7",
        "--skip-neural-training",
        "--max-standard-cases",
        "200",
        "--max-mp-cases",
        "-1",
        "--max-csm-cases",
        "-1",
        "--max-nonholonomic-cases",
        "0",
        "--max-ablation-cases",
        "100",
        "--max-exp4-cases",
        "-1",
        "--grid-max-expansions",
        "50000",
        "--hybrid-max-expansions",
        "12000",
        "--hybrid-hard-max-expansions",
        "13000",
        "--hybrid-maze-max-expansions",
        "18000",
        "--hybrid-exp4-max-expansions",
        "20000",
        "--hybrid-budget-cap",
        "7000",
        "--sampling-max-iters",
        "1500",
        "--rs-field-yaw-bins",
        "24",
        "--residual-alpha",
        f"{params.residual_alpha:.6f}",
        "--residual-clip",
        "28.0",
        "--residual-bias-quantile",
        "0.25",
        "--residual-corridor-threshold",
        "0.9",
        "--residual-corridor-suppress",
        "0.3",
        "--residual-topq-quantile",
        "0.1",
        "--residual-contrastive-bg-quantile",
        "0.62",
        "--residual-contrastive-neg-scale",
        "0.16",
        "--residual-contrastive-pos-scale",
        "1.25",
        "--residual-floor-ratio",
        "0.62",
        "--residual-transport-iters",
        "0",
        "--residual-transport-step",
        "0.35",
        "--residual-transport-clearance-sigma",
        "0.45",
        "--residual-bottleneck-threshold",
        "0.0",
        "--residual-bottleneck-blend",
        "0.0",
        "--residual-bottleneck-gamma",
        "1.0",
        "--residual-open-boost",
        "0.45",
        "--residual-open-boost-topq",
        "0.9",
        "--residual-open-boost-min-line-clearance",
        "1.8",
        "--residual-bottleneck-dampen",
        "0.95",
        "--residual-adaptive-trust-ratio",
        "0.0",
        "--residual-adaptive-trust-quantile",
        "0.95",
        "--esdf-anchor-alpha",
        "0.15",
        "--esdf-anchor-threshold",
        "1.3",
        "--max-public-cases",
        "40",
        "--standard-base-mode",
        "euclidean",
    ]
    if base_quick:
        common_args += ["--max-exp3-cases", "8"]
    else:
        common_args += ["--max-exp3-cases", "0"]

    _run(common_args)
    metrics = _parse_exp3_metrics(out_dir / "exp_results_summary.csv")
    obj = _objective(
        success_full=metrics["success_full"],
        success_nores=metrics["success_nores"],
        dE_percent=metrics["dE_percent"],
        dT_percent=metrics["dT_percent"],
        dE_narrow_percent=metrics["dE_narrow_percent"],
        dE_maze_percent=metrics["dE_maze_percent"],
        cfg=obj_cfg,
    )
    return EvalResult(
        split=split,
        params=params,
        paper_out=str(out_dir.relative_to(ROOT)),
        checkpoint=str(ckpt_path.relative_to(ROOT)),
        success_full=float(metrics["success_full"]),
        success_nores=float(metrics["success_nores"]),
        dE_percent=float(metrics["dE_percent"]),
        dT_percent=float(metrics["dT_percent"]),
        full_expansions=float(metrics["full_expansions"]),
        nores_expansions=float(metrics["nores_expansions"]),
        full_time_ms=float(metrics["full_time_ms"]),
        nores_time_ms=float(metrics["nores_time_ms"]),
        dE_narrow_percent=float(metrics["dE_narrow_percent"]),
        dE_maze_percent=float(metrics["dE_maze_percent"]),
        dE_other_percent=float(metrics["dE_other_percent"]),
        objective=float(obj),
        source="ran",
    )


def _load_warm_start(obj_cfg: ObjectiveConfig) -> list[EvalResult]:
    # Reuse known quick observations from current workspace.
    warm_specs: list[tuple[Params, str]] = [
        (Params(0.00, 0.60, 0.35, 0.20, 0.55), "outputs/paper/interp_stage_q8_si06_r055/exp_results_summary.csv"),
        (Params(0.00, 0.60, 0.35, 0.20, 0.60), "outputs/paper/interp_stage_q8_si06_r060/exp_results_summary.csv"),
        (Params(0.00, 0.60, 0.35, 0.20, 0.70), "outputs/paper/interp_stage_q8_si06_r070/exp_results_summary.csv"),
        (Params(0.00, 0.65, 0.35, 0.20, 0.70), "outputs/paper/interp_stage_q8_sj01_r070/exp_results_summary.csv"),
        (Params(0.00, 0.60, 0.30, 0.15, 0.70), "outputs/paper/interp_stage_q8_sj02_r070/exp_results_summary.csv"),
        (Params(0.00, 0.55, 0.35, 0.20, 0.70), "outputs/paper/interp_stage_q8_sj03_r070/exp_results_summary.csv"),
        (Params(0.00, 0.65, 0.30, 0.15, 0.70), "outputs/paper/interp_stage_q8_sj04_r070/exp_results_summary.csv"),
        (Params(0.02, 0.60, 0.35, 0.20, 0.70), "outputs/paper/interp_stage_q8_sj05_r070/exp_results_summary.csv"),
        # BO v2 quick observations (if available).
        (
            Params(0.014859940862507224, 0.5381540024128737, 0.3704885020175581, 0.2021014346227139, 0.700021330404563),
            "outputs/paper/bo_stagewise_v2_quick_t000/exp_results_summary.csv",
        ),
        (
            Params(0.07372225068128815, 0.45129390240717115, 0.3201928273478037, 0.2130317445914303, 0.7034426736114455),
            "outputs/paper/bo_stagewise_v2_quick_t001/exp_results_summary.csv",
        ),
        (
            Params(0.022404532377757892, 0.5243371361145593, 0.42, 0.22177082720402155, 0.6996503704189676),
            "outputs/paper/bo_stagewise_v2_quick_t002/exp_results_summary.csv",
        ),
        (
            Params(0.02270150838078706, 0.4911426557900717, 0.42, 0.25294269361127475, 0.699546280597182),
            "outputs/paper/bo_stagewise_v2_quick_t003/exp_results_summary.csv",
        ),
    ]
    out: list[EvalResult] = []
    for i, (p, rel_csv) in enumerate(warm_specs):
        csv_path = ROOT / rel_csv
        if not csv_path.exists():
            continue
        metrics = _parse_exp3_metrics(csv_path)
        obj = _objective(
            success_full=metrics["success_full"],
            success_nores=metrics["success_nores"],
            dE_percent=metrics["dE_percent"],
            dT_percent=metrics["dT_percent"],
            dE_narrow_percent=metrics["dE_narrow_percent"],
            dE_maze_percent=metrics["dE_maze_percent"],
            cfg=obj_cfg,
        )
        out.append(
            EvalResult(
                split="quick",
                params=p,
                paper_out=str(csv_path.parent.relative_to(ROOT)),
                checkpoint="",
                success_full=float(metrics["success_full"]),
                success_nores=float(metrics["success_nores"]),
                dE_percent=float(metrics["dE_percent"]),
                dT_percent=float(metrics["dT_percent"]),
                full_expansions=float(metrics["full_expansions"]),
                nores_expansions=float(metrics["nores_expansions"]),
                full_time_ms=float(metrics["full_time_ms"]),
                nores_time_ms=float(metrics["nores_time_ms"]),
                dE_narrow_percent=float(metrics["dE_narrow_percent"]),
                dE_maze_percent=float(metrics["dE_maze_percent"]),
                dE_other_percent=float(metrics["dE_other_percent"]),
                objective=float(obj),
                source=f"warm{i}",
            )
        )
    return out


def _load_warm_start_full(obj_cfg: ObjectiveConfig) -> list[EvalResult]:
    # Reuse known full observations for direct-full BO.
    warm_specs: list[tuple[Params, str]] = [
        (Params(0.00, 0.55, 0.35, 0.20, 0.70), "outputs/paper/interp_stage_q8_sj03_r070_exp3_full/exp_results_summary.csv"),
        (Params(0.00, 0.60, 0.35, 0.20, 0.70), "outputs/paper/interp_stage_q8_si06_r070_exp3_full/exp_results_summary.csv"),
        (Params(0.00, 0.65, 0.35, 0.20, 0.70), "outputs/paper/interp_stage_q8_sj01_r070_exp3_full/exp_results_summary.csv"),
        (
            Params(0.02270150838078706, 0.4911426557900717, 0.42, 0.25294269361127475, 0.699546280597182),
            "outputs/paper/bo_stagewise_v2_full_top00/exp_results_summary.csv",
        ),
        (
            Params(0.022404532377757892, 0.5243371361145593, 0.42, 0.22177082720402155, 0.6996503704189676),
            "outputs/paper/bo_stagewise_v2_full_top01/exp_results_summary.csv",
        ),
        (
            Params(0.0014764181162839453, 0.48675279240175684, 0.5471514467172082, 0.25752097647106664, 0.7383420211799772),
            "outputs/paper/bo_stagewise_v3_full_top00/exp_results_summary.csv",
        ),
        (
            Params(0.0053333943498809116, 0.52842551276045, 0.547079755227908, 0.298807413088527, 0.7392806862481437),
            "outputs/paper/bo_stagewise_v3_full_top01/exp_results_summary.csv",
        ),
        (
            Params(0.010868779769321374, 0.46, 0.3891967941922955, 0.26491948296599416, 0.6783890738855962),
            "outputs/paper/bo_stagewise_v4_full_full_t000/exp_results_summary.csv",
        ),
        (
            Params(0.011745806496500491, 0.46, 0.4127744078652651, 0.2440134570484997, 0.6762535162625803),
            "outputs/paper/bo_stagewise_v4_full_full_t001/exp_results_summary.csv",
        ),
        (
            Params(0.0218220778779001, 0.46, 0.4120157153673849, 0.25406236303069013, 0.73),
            "outputs/paper/bo_stagewise_v4_full_full_t002/exp_results_summary.csv",
        ),
        (
            Params(0.03, 0.4, 0.4151817901622581, 0.23, 0.7272282401814921),
            "outputs/paper/bo_stagewise_v5_full_full_t000/exp_results_summary.csv",
        ),
        (
            Params(0.017678663583250986, 0.4172088968644411, 0.4194880686075313, 0.2466508522231234, 0.7999985498234818),
            "outputs/paper/bo_stagewise_v5_full_full_t001/exp_results_summary.csv",
        ),
        (
            Params(0.026361268258069313, 0.4, 0.39, 0.24425438521456516, 0.72),
            "outputs/paper/bo_stagewise_v5_full_full_t002/exp_results_summary.csv",
        ),
        (
            Params(0.034467273980734334, 0.372123162511512, 0.41027352259644057, 0.255984697495828, 0.7579397296228868),
            "outputs/paper/bo_stagewise_v6_scene_full_full_t000/exp_results_summary.csv",
        ),
        (
            Params(0.03313835359859231, 0.36144161529863394, 0.4211880546247331, 0.22181421846900953, 0.7345067651526537),
            "outputs/paper/bo_stagewise_v6_scene_full_full_t001/exp_results_summary.csv",
        ),
        (
            Params(0.013949438879528904, 0.4715203325082031, 0.38766163849525237, 0.219975653823014, 0.7287224531388679),
            "outputs/paper/bo_stagewise_v6_scene_full_full_t002/exp_results_summary.csv",
        ),
        (
            Params(0.06421949148724404, 0.3494444059491577, 0.40217570523615626, 0.2260275903089949, 0.7323495964504654),
            "outputs/paper/bo_stagewise_v7_scene_full_full_t000/exp_results_summary.csv",
        ),
        (
            Params(0.04109310480047003, 0.28131952281319766, 0.4305841225959826, 0.1974858513753444, 0.7321775677084328),
            "outputs/paper/bo_stagewise_v7_scene_full_full_t001/exp_results_summary.csv",
        ),
        (
            Params(0.04114777613760216, 0.29621063144346654, 0.4132116403545485, 0.19084878336415184, 0.7327596480054501),
            "outputs/paper/bo_stagewise_v7_scene_full_full_t002/exp_results_summary.csv",
        ),
        (
            Params(0.06863498112486624, 0.18635743395611373, 0.4278490022158788, 0.18976537879521144, 0.7336050536344496),
            "outputs/paper/bo_stagewise_v8_scene_full_full_t000/exp_results_summary.csv",
        ),
        (
            Params(0.07046482760854303, 0.18, 0.44335799761403166, 0.22, 0.72),
            "outputs/paper/bo_stagewise_v8_scene_full_full_t001/exp_results_summary.csv",
        ),
        (
            Params(0.055696291568343506, 0.18, 0.4280459450669149, 0.18836371222958662, 0.72),
            "outputs/paper/bo_stagewise_v8_scene_full_full_t002/exp_results_summary.csv",
        ),
        (
            Params(0.09593743039280792, 0.10924928672035142, 0.4416368198735182, 0.22662185493298215, 0.7086229023248901),
            "outputs/paper/bo_stagewise_v9_scene_full_full_t000/exp_results_summary.csv",
        ),
        (
            Params(0.07768803663119196, 0.10919047809110592, 0.48954896196189324, 0.2780225206569793, 0.6809650197326299),
            "outputs/paper/bo_stagewise_v9_scene_full_full_t001/exp_results_summary.csv",
        ),
    ]
    out: list[EvalResult] = []
    for i, (p, rel_csv) in enumerate(warm_specs):
        csv_path = ROOT / rel_csv
        if not csv_path.exists():
            continue
        metrics = _parse_exp3_metrics(csv_path)
        obj = _objective(
            success_full=metrics["success_full"],
            success_nores=metrics["success_nores"],
            dE_percent=metrics["dE_percent"],
            dT_percent=metrics["dT_percent"],
            dE_narrow_percent=metrics["dE_narrow_percent"],
            dE_maze_percent=metrics["dE_maze_percent"],
            cfg=obj_cfg,
        )
        out.append(
            EvalResult(
                split="full",
                params=p,
                paper_out=str(csv_path.parent.relative_to(ROOT)),
                checkpoint="",
                success_full=float(metrics["success_full"]),
                success_nores=float(metrics["success_nores"]),
                dE_percent=float(metrics["dE_percent"]),
                dT_percent=float(metrics["dT_percent"]),
                full_expansions=float(metrics["full_expansions"]),
                nores_expansions=float(metrics["nores_expansions"]),
                full_time_ms=float(metrics["full_time_ms"]),
                nores_time_ms=float(metrics["nores_time_ms"]),
                dE_narrow_percent=float(metrics["dE_narrow_percent"]),
                dE_maze_percent=float(metrics["dE_maze_percent"]),
                dE_other_percent=float(metrics["dE_other_percent"]),
                objective=float(obj),
                source=f"warm_full{i}",
            )
        )
    return out


def _bounds(args: argparse.Namespace) -> tuple[np.ndarray, np.ndarray]:
    lo = np.array(
        [
            args.bound_shallow_min,
            args.bound_deep_min,
            args.bound_decoder_min,
            args.bound_head_min,
            args.bound_residual_min,
        ],
        dtype=np.float64,
    )
    hi = np.array(
        [
            args.bound_shallow_max,
            args.bound_deep_max,
            args.bound_decoder_max,
            args.bound_head_max,
            args.bound_residual_max,
        ],
        dtype=np.float64,
    )
    if np.any(lo >= hi):
        raise ValueError(f"Invalid bounds: lo={lo}, hi={hi}")
    return lo, hi


def _from_array(x: np.ndarray) -> Params:
    return Params(
        alpha_shallow=float(x[0]),
        alpha_deep=float(x[1]),
        alpha_decoder=float(x[2]),
        alpha_head=float(x[3]),
        residual_alpha=float(x[4]),
    )


def _fit_gp(X: np.ndarray, y: np.ndarray) -> GaussianProcessRegressor:
    kernel = ConstantKernel(1.0, (1e-3, 1e3)) * Matern(length_scale=np.ones(X.shape[1]), nu=2.5) + WhiteKernel(
        noise_level=1e-3, noise_level_bounds=(1e-8, 1e-1)
    )
    gp = GaussianProcessRegressor(
        kernel=kernel,
        alpha=1e-6,
        normalize_y=True,
        n_restarts_optimizer=4,
        random_state=0,
    )
    gp.fit(X, y)
    return gp


def _expected_improvement(mu: np.ndarray, sigma: np.ndarray, best_y: float, xi: float) -> np.ndarray:
    imp = best_y - mu - xi
    z = np.zeros_like(imp)
    nz = sigma > 1e-12
    z[nz] = imp[nz] / sigma[nz]
    ei = np.zeros_like(mu)
    ei[nz] = imp[nz] * norm.cdf(z[nz]) + sigma[nz] * norm.pdf(z[nz])
    return ei


def _propose(
    rng: np.random.Generator,
    observed: list[EvalResult],
    lo: np.ndarray,
    hi: np.ndarray,
    candidate_pool: int,
    xi: float,
    seen: set[tuple[float, float, float, float, float]],
) -> Params:
    if len(observed) < 3:
        for _ in range(5000):
            x = rng.uniform(lo, hi)
            p = _from_array(x)
            if p.rounded_key() not in seen:
                return p
        raise RuntimeError("Failed to sample initial random candidate.")

    X = np.vstack([r.params.to_array() for r in observed])
    y = np.array([r.objective for r in observed], dtype=np.float64)
    gp = _fit_gp(X, y)

    # Global random candidate pool + local perturbations around best.
    cand_global = rng.uniform(lo, hi, size=(candidate_pool, len(lo)))
    best_x = observed[int(np.argmin(y))].params.to_array()
    local = best_x + rng.normal(loc=0.0, scale=np.array([0.01, 0.03, 0.02, 0.02, 0.03]), size=(candidate_pool // 2, len(lo)))
    local = np.clip(local, lo, hi)
    cand = np.vstack([cand_global, local])

    mu, sigma = gp.predict(cand, return_std=True)
    ei = _expected_improvement(mu=mu, sigma=sigma, best_y=float(np.min(y)), xi=float(xi))
    order = np.argsort(-ei)
    for idx in order:
        p = _from_array(cand[idx])
        if p.rounded_key() not in seen:
            return p

    # Fallback random sampling if EI candidates are duplicates.
    for _ in range(5000):
        x = rng.uniform(lo, hi)
        p = _from_array(x)
        if p.rounded_key() not in seen:
            return p
    raise RuntimeError("Failed to find non-duplicate BO candidate.")


def _write_results(path: Path, rows: Iterable[EvalResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "split",
        "source",
        "alpha_shallow",
        "alpha_deep",
        "alpha_decoder",
        "alpha_head",
        "residual_alpha",
        "success_full",
        "success_nores",
        "dE_percent",
        "dT_percent",
        "dE_narrow_percent",
        "dE_maze_percent",
        "dE_other_percent",
        "full_expansions",
        "nores_expansions",
        "full_time_ms",
        "nores_time_ms",
        "objective",
        "paper_out",
        "checkpoint",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            row = {
                "split": r.split,
                "source": r.source,
                "alpha_shallow": r.params.alpha_shallow,
                "alpha_deep": r.params.alpha_deep,
                "alpha_decoder": r.params.alpha_decoder,
                "alpha_head": r.params.alpha_head,
                "residual_alpha": r.params.residual_alpha,
                "success_full": r.success_full,
                "success_nores": r.success_nores,
                "dE_percent": r.dE_percent,
                "dT_percent": r.dT_percent,
                "dE_narrow_percent": r.dE_narrow_percent,
                "dE_maze_percent": r.dE_maze_percent,
                "dE_other_percent": r.dE_other_percent,
                "full_expansions": r.full_expansions,
                "nores_expansions": r.nores_expansions,
                "full_time_ms": r.full_time_ms,
                "nores_time_ms": r.nores_time_ms,
                "objective": r.objective,
                "paper_out": r.paper_out,
                "checkpoint": r.checkpoint,
            }
            w.writerow(row)


def main() -> None:
    args = _parse_args()
    obj_cfg = ObjectiveConfig(
        scene_penalty_narrow=float(args.scene_penalty_narrow),
        scene_penalty_maze=float(args.scene_penalty_maze),
        scene_tol_narrow=float(args.scene_tol_narrow),
        scene_tol_maze=float(args.scene_tol_maze),
        time_penalty_threshold=float(args.time_penalty_threshold),
        time_penalty_weight=float(args.time_penalty_weight),
    )
    use_warm = bool(args.warm_start) and not bool(args.no_warm_start)
    lo, hi = _bounds(args)
    rng = np.random.default_rng(int(args.seed))

    opt_split = str(args.bo_split)
    if opt_split not in {"quick", "full"}:
        raise ValueError(f"Unsupported bo-split: {opt_split}")

    bo_obs: list[EvalResult] = []
    if use_warm:
        if opt_split == "quick":
            bo_obs.extend(_load_warm_start(obj_cfg=obj_cfg))
        else:
            bo_obs.extend(_load_warm_start_full(obj_cfg=obj_cfg))
    print(f"[bo] warm_start={use_warm} split={opt_split} loaded={len(bo_obs)}", flush=True)

    seen: set[tuple[float, float, float, float, float]] = {r.params.rounded_key() for r in bo_obs}

    for i in range(int(args.n_bo_trials)):
        p = _propose(
            rng=rng,
            observed=bo_obs,
            lo=lo,
            hi=hi,
            candidate_pool=int(args.candidate_pool),
            xi=float(args.xi),
            seen=seen,
        )
        seen.add(p.rounded_key())
        trial_id = f"t{i:03d}"
        print(f"[bo] {opt_split} trial {i+1}/{args.n_bo_trials} params={asdict(p)}", flush=True)
        r = _eval_trial(
            trial_id=trial_id,
            split=opt_split,
            params=p,
            ckpt_old=args.ckpt_old,
            ckpt_new=args.ckpt_new,
            bn_stat_source=str(args.bn_stat_source),
            device=str(args.device),
            search_name=str(args.search_name),
            base_quick=(opt_split == "quick"),
            obj_cfg=obj_cfg,
        )
        bo_obs.append(r)
        print(
            f"[bo] {opt_split} result trial={trial_id} dE={r.dE_percent:+.3f}% dT={r.dT_percent:+.3f}% "
            f"sr={r.success_full:.4f}/{r.success_nores:.4f} obj={r.objective:+.3f}",
            flush=True,
        )

    quick_obs: list[EvalResult] = []
    full_obs: list[EvalResult] = []
    if opt_split == "quick":
        quick_obs = list(bo_obs)
        quick_ranked = sorted(quick_obs, key=lambda x: (x.objective, x.dE_percent, x.dT_percent))
        top_candidates: list[EvalResult] = []
        used = set()
        for r in quick_ranked:
            k = r.params.rounded_key()
            if k in used:
                continue
            used.add(k)
            top_candidates.append(r)
            if len(top_candidates) >= int(min(args.topk_full, args.max_full_candidates)):
                break

        for j, qr in enumerate(top_candidates):
            trial_id = f"top{j:02d}"
            print(f"[bo] promote to full {j+1}/{len(top_candidates)} params={asdict(qr.params)}", flush=True)
            fr = _eval_trial(
                trial_id=trial_id,
                split="full",
                params=qr.params,
                ckpt_old=args.ckpt_old,
                ckpt_new=args.ckpt_new,
                bn_stat_source=str(args.bn_stat_source),
                device=str(args.device),
                search_name=str(args.search_name),
                base_quick=False,
                obj_cfg=obj_cfg,
            )
            full_obs.append(fr)
            print(
                f"[bo] full result trial={trial_id} dE={fr.dE_percent:+.3f}% dT={fr.dT_percent:+.3f}% "
                f"sr={fr.success_full:.4f}/{fr.success_nores:.4f} obj={fr.objective:+.3f}",
                flush=True,
            )
    else:
        full_obs = list(bo_obs)

    all_rows = list(quick_obs) + list(full_obs)
    out_dir = ROOT / "outputs" / "paper" / str(args.search_name)
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_results(out_dir / "bo_results.csv", all_rows)

    best_quick = min(quick_obs, key=lambda x: x.objective) if quick_obs else None
    best_full = min(full_obs, key=lambda x: x.objective) if full_obs else None
    summary = {
        "search_name": str(args.search_name),
        "bo_split": opt_split,
        "n_quick_total": len(quick_obs),
        "n_quick_new": int(args.n_bo_trials),
        "n_full": len(full_obs),
        "objective_config": asdict(obj_cfg),
        "best_quick": asdict(best_quick) if best_quick is not None else None,
        "best_full": asdict(best_full) if best_full is not None else None,
        "bounds": {
            "alpha_shallow": [float(lo[0]), float(hi[0])],
            "alpha_deep": [float(lo[1]), float(hi[1])],
            "alpha_decoder": [float(lo[2]), float(hi[2])],
            "alpha_head": [float(lo[3]), float(hi[3])],
            "residual_alpha": [float(lo[4]), float(hi[4])],
        },
    }
    (out_dir / "bo_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[bo] wrote", out_dir / "bo_results.csv", flush=True)
    print("[bo] wrote", out_dir / "bo_summary.json", flush=True)
    if best_full is not None:
        print(
            f"[bo] BEST FULL dE={best_full.dE_percent:+.3f}% dT={best_full.dT_percent:+.3f}% "
            f"params={asdict(best_full.params)} out={best_full.paper_out}",
            flush=True,
        )
    elif best_quick is not None:
        print(
            f"[bo] BEST QUICK dE={best_quick.dE_percent:+.3f}% dT={best_quick.dT_percent:+.3f}% "
            f"params={asdict(best_quick.params)} out={best_quick.paper_out}",
            flush=True,
        )


if __name__ == "__main__":
    main()
