from __future__ import annotations

import hashlib
import json
import warnings
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _as_str_dict(d: dict[str, Any], keys: tuple[str, ...]) -> dict[str, str]:
    out: dict[str, str] = {}
    for k in keys:
        v = d.get(k, "")
        out[k] = "" if v is None else str(v)
    return out


def _as_int(v: Any, name: str) -> int:
    try:
        return int(v)
    except Exception as exc:
        raise ValueError(f"Invalid int field {name}: {v!r}") from exc


def _as_float(v: Any, name: str) -> float:
    try:
        return float(v)
    except Exception as exc:
        raise ValueError(f"Invalid float field {name}: {v!r}") from exc


def _load_joblib(path: Path):
    try:
        import joblib  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("Missing dependency: joblib (required for policy artifact models)") from exc
    return joblib.load(path)


@dataclass(frozen=True)
class RouterPolicyV1Config:
    version: str
    epsilon_rel: float
    # Static feature extraction config (must match protocol tooling).
    static_router_args: SimpleNamespace

    # Model files + schemas.
    conformal_clf_path: Path
    conformal_clf_columns: list[str]
    cost_reg_path: Path
    cost_reg_columns: list[str]
    probe_gain_reg_path: Path
    probe_gain_reg_columns: list[str]

    # Conformal policy params.
    alpha_conformal: float
    score_power_a: float
    score_cost_power_b: float
    q_by_difficulty: dict[str, float]
    c_ref_calib_median_ms: float
    tau_conformal_by_difficulty: dict[str, float]

    # Probe policy params.
    probe_max_expansions: int
    gain_power: float
    w_hard: float
    w_bottleneck: float
    w_stall: float
    tau_probe_by_difficulty: dict[str, float]


@dataclass
class RouterPolicyV1:
    cfg: RouterPolicyV1Config
    _conformal_clf: Any
    _cost_reg: Any
    _probe_gain_reg: Any
    _conformal_col_index: dict[str, int]
    _cost_col_index: dict[str, int]
    _probe_gain_col_index: dict[str, int]

    @staticmethod
    def default_static_router_args() -> SimpleNamespace:
        # Must match `scripts/run_router_diagnosis.py:_default_router_args`.
        return SimpleNamespace(
            router_corridor_radius_cells=2,
            router_samples_per_cell=1.0,
            router_fast_max_distance_ratio=0.75,
            router_fast_max_line_block_ratio=0.30,
            router_fast_max_local_occ_ratio=0.40,
            router_fast_max_global_occ_ratio=0.55,
            router_slow_min_line_block_ratio=0.65,
            router_slow_min_local_occ_ratio=0.60,
            router_score_threshold=0.47,
            router_w_line_block=0.42,
            router_w_local_occ=0.33,
            router_w_distance=0.18,
            router_w_global_occ=0.07,
            router_los_penalty=0.08,
            router_fast_score_margin=0.06,
        )

    @classmethod
    def load(cls, artifact_dir: Path) -> "RouterPolicyV1":
        artifact_dir = Path(artifact_dir)
        policy_json = artifact_dir / "policy.json"
        if not policy_json.exists():
            raise FileNotFoundError(f"Missing policy JSON: {policy_json}")
        obj = read_json(policy_json)

        version = str(obj.get("version", ""))
        if version != "router_policy_v1":
            raise ValueError(f"Unsupported policy version: {version!r}")

        protocol = obj.get("protocol", {})
        eps = _as_float(protocol.get("epsilon_rel", 0.015), "protocol.epsilon_rel")

        static_args_obj = obj.get("static_feature_args", {})
        static_args = SimpleNamespace(**static_args_obj) if static_args_obj else cls.default_static_router_args()

        models = obj.get("models", {})
        conformal = models.get("conformal_violation_clf", {})
        cost = models.get("cost_regressor", {})
        probe_gain = models.get("probe_gain_regressor", {})

        conformal_path = artifact_dir / str(conformal.get("joblib", ""))
        cost_path = artifact_dir / str(cost.get("joblib", ""))
        probe_gain_path = artifact_dir / str(probe_gain.get("joblib", ""))
        for p in (conformal_path, cost_path, probe_gain_path):
            if not p.exists():
                raise FileNotFoundError(f"Missing model file: {p}")

        conformal_cols = list(conformal.get("columns", []))
        cost_cols = list(cost.get("columns", []))
        probe_cols = list(probe_gain.get("columns", []))
        if not conformal_cols or not cost_cols or not probe_cols:
            raise ValueError("Missing model columns in policy.json (conformal/cost/probe_gain).")

        conf_cfg = obj.get("conformal", {})
        alpha = _as_float(conf_cfg.get("alpha_conformal", 0.65), "conformal.alpha_conformal")
        a = _as_float(conf_cfg.get("score_power_a", 1.0), "conformal.score_power_a")
        b = _as_float(conf_cfg.get("score_cost_power_b", 1.0), "conformal.score_cost_power_b")
        q_by_diff = {k: float(v) for k, v in (conf_cfg.get("q_by_difficulty", {}) or {}).items()}
        c_ref = _as_float(conf_cfg.get("c_ref_calib_median_ms", 1.0), "conformal.c_ref_calib_median_ms")
        tau_conf = {k: float(v) for k, v in (conf_cfg.get("tau_by_difficulty", {}) or {}).items()}

        probe_cfg = obj.get("probe", {})
        max_exp = _as_int(probe_cfg.get("max_expansions", 96), "probe.max_expansions")
        gain_power = _as_float(probe_cfg.get("gain_power", 1.0), "probe.gain_power")
        w_hard = _as_float(probe_cfg.get("w_hard", 0.5), "probe.w_hard")
        w_bottle = _as_float(probe_cfg.get("w_bottleneck", 0.0), "probe.w_bottleneck")
        w_stall = _as_float(probe_cfg.get("w_stall", 0.0), "probe.w_stall")
        tau_probe = {k: float(v) for k, v in (probe_cfg.get("tau_by_difficulty", {}) or {}).items()}

        cfg = RouterPolicyV1Config(
            version=version,
            epsilon_rel=eps,
            static_router_args=static_args,
            conformal_clf_path=conformal_path,
            conformal_clf_columns=conformal_cols,
            cost_reg_path=cost_path,
            cost_reg_columns=cost_cols,
            probe_gain_reg_path=probe_gain_path,
            probe_gain_reg_columns=probe_cols,
            alpha_conformal=alpha,
            score_power_a=a,
            score_cost_power_b=b,
            q_by_difficulty=q_by_diff,
            c_ref_calib_median_ms=c_ref,
            tau_conformal_by_difficulty=tau_conf,
            probe_max_expansions=max_exp,
            gain_power=gain_power,
            w_hard=w_hard,
            w_bottleneck=w_bottle,
            w_stall=w_stall,
            tau_probe_by_difficulty=tau_probe,
        )
        conformal_cols = list(cfg.conformal_clf_columns)
        cost_cols = list(cfg.cost_reg_columns)
        probe_cols = list(cfg.probe_gain_reg_columns)
        return cls(
            cfg=cfg,
            _conformal_clf=_load_joblib(conformal_path),
            _cost_reg=_load_joblib(cost_path),
            _probe_gain_reg=_load_joblib(probe_gain_path),
            _conformal_col_index={c: i for i, c in enumerate(conformal_cols)},
            _cost_col_index={c: i for i, c in enumerate(cost_cols)},
            _probe_gain_col_index={c: i for i, c in enumerate(probe_cols)},
        )

    def _vector_from_features(
        self,
        col_index: dict[str, int],
        numeric: dict[str, float],
        categorical: dict[str, str],
    ) -> np.ndarray:
        x = np.zeros((1, len(col_index)), dtype=np.float64)

        for k, v in numeric.items():
            j = col_index.get(k)
            if j is not None:
                x[0, j] = float(v)

        for k, v in categorical.items():
            key = f"{k}_{v}"
            j = col_index.get(key)
            if j is not None:
                x[0, j] = 1.0
        return x

    def conformal_score(
        self,
        *,
        difficulty: str,
        source_dataset: str,
        scenario: str,
        map_id: str,
        ood_family: int,
        static_feat: dict[str, float | bool],
        fast_metrics: dict[str, float],
    ) -> tuple[float, dict[str, float]]:
        numeric = {
            "line_block_ratio": float(static_feat["line_block_ratio"]),
            "local_occ_ratio": float(static_feat["local_occ_ratio"]),
            "global_occ_ratio": float(static_feat["global_occ_ratio"]),
            "distance_ratio": float(static_feat["distance_ratio"]),
            "complexity_score": float(static_feat["complexity_score"]),
            "los_clear": float(bool(static_feat["los_clear"])),
            "L_fast": float(fast_metrics["L_fast"]),
            "T_fast_ms": float(fast_metrics["T_fast_ms"]),
            "search_fast_ms": float(fast_metrics["search_fast_ms"]),
            "path_len_fast": float(fast_metrics["path_len_fast"]),
            "ood_family": float(int(ood_family)),
        }
        cat = _as_str_dict(
            {
                "difficulty": difficulty,
                "source_dataset": source_dataset,
                "scenario": scenario,
                "map_id": map_id,
            },
            ("difficulty", "source_dataset", "scenario", "map_id"),
        )
        x = self._vector_from_features(
            self._conformal_col_index,
            numeric=numeric,
            categorical=cat,
        )
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message="X does not have valid feature names, but .* was fitted with feature names",
            )
            p_hat = float(self._conformal_clf.predict_proba(x)[0, 1])
        q = float(self.cfg.q_by_difficulty.get(str(difficulty), 0.0))
        p_upper = float(np.clip(p_hat + q, 0.0, 1.0))

        x_cost = self._vector_from_features(
            self._cost_col_index,
            numeric=numeric,
            categorical=cat,
        )
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message="X does not have valid feature names, but .* was fitted with feature names",
            )
            c_hat = float(self._cost_reg.predict(x_cost)[0])
        c_hat = float(max(c_hat, 1e-6))
        c_ref = float(max(self.cfg.c_ref_calib_median_ms, 1e-6))
        c_norm = float(max(c_hat / c_ref, 1e-6))

        a = float(self.cfg.score_power_a)
        b = float(self.cfg.score_cost_power_b)
        score = float((max(p_upper, 1e-9) ** a) / (c_norm**b))
        meta = {
            "p_hat": p_hat,
            "p_upper": p_upper,
            "c_hat_ms": c_hat,
            "c_norm": c_norm,
        }
        return score, meta

    def probe_score(
        self,
        *,
        difficulty: str,
        source_dataset: str,
        scenario: str,
        map_id: str,
        ood_family: int,
        static_feat: dict[str, float | bool],
        probe_feat: dict[str, float],
        fast_metrics: dict[str, float],
    ) -> tuple[float, dict[str, float]]:
        numeric = {
            # Probe features.
            "probe_success": float(probe_feat["probe_success"]),
            "probe_expansions": float(probe_feat["probe_expansions"]),
            "probe_runtime_ms": float(probe_feat["probe_runtime_ms"]),
            "probe_expansion_ratio": float(probe_feat["probe_expansion_ratio"]),
            "probe_h_drop_ratio": float(probe_feat["probe_h_drop_ratio"]),
            "probe_progress_per_exp": float(probe_feat["probe_progress_per_exp"]),
            "probe_open_growth": float(probe_feat["probe_open_growth"]),
            "probe_branching": float(probe_feat["probe_branching"]),
            "probe_improve_rate": float(probe_feat["probe_improve_rate"]),
            "probe_bottleneck_rate": float(probe_feat["probe_bottleneck_rate"]),
            "probe_deadend_rate": float(probe_feat.get("probe_deadend_rate", 0.0)),
            # Static features.
            "line_block_ratio": float(static_feat["line_block_ratio"]),
            "local_occ_ratio": float(static_feat["local_occ_ratio"]),
            "global_occ_ratio": float(static_feat["global_occ_ratio"]),
            "distance_ratio": float(static_feat["distance_ratio"]),
            "complexity_score": float(static_feat["complexity_score"]),
            # Fast metrics.
            "L_fast": float(fast_metrics["L_fast"]),
            "T_fast_ms": float(fast_metrics["T_fast_ms"]),
            "search_fast_ms": float(fast_metrics["search_fast_ms"]),
            "path_len_fast": float(fast_metrics["path_len_fast"]),
            "ood_family": float(int(ood_family)),
        }
        cat = _as_str_dict(
            {
                "difficulty": difficulty,
                "source_dataset": source_dataset,
                "scenario": scenario,
                "map_id": map_id,
            },
            ("difficulty", "source_dataset", "scenario", "map_id"),
        )
        x_gain = self._vector_from_features(
            self._probe_gain_col_index,
            numeric=numeric,
            categorical=cat,
        )
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message="X does not have valid feature names, but .* was fitted with feature names",
            )
            pred_gain = float(self._probe_gain_reg.predict(x_gain)[0])
        pred_gain = float(max(pred_gain, 0.0))

        hard = 1.0 if str(difficulty) == "hard" else 0.0
        bottle = float(np.clip(numeric["probe_bottleneck_rate"], 0.0, 1.0))
        stall = float(np.clip(1.0 - float(numeric["probe_h_drop_ratio"]), 0.0, 1.0))
        mult = 1.0 + float(self.cfg.w_hard) * hard + float(self.cfg.w_bottleneck) * bottle + float(self.cfg.w_stall) * stall
        score = float((pred_gain ** float(self.cfg.gain_power)) * mult)
        meta = {
            "pred_gain": pred_gain,
            "mult": mult,
        }
        return score, meta
