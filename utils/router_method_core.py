from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist
from typing import Any, Protocol

import numpy as np


@dataclass(frozen=True)
class RiskBudgetProtocol:
    """
    Minimal protocol for risk-bounded adaptive compute routing.

    - epsilon_rel: violation threshold on relative quality loss.
    - alpha: risk budget (target upper bound for violation probability).
    """

    epsilon_rel: float = 0.015
    alpha: float = 0.05


@dataclass(frozen=True)
class CounterfactualSchema:
    sample_id: str = "sample_name"
    group: str = "difficulty"

    # Quality (slow is the reference arm).
    l_fast: str = "L_fast"
    l_slow: str = "L_slow"

    # Latency.
    t_fast_ms: str = "T_fast_ms"
    t_slow_ms: str = "T_slow_ms"

    # Optional precomputed columns (if absent, they will be derived when needed).
    q_rel: str = "q_rel"  # (L_fast - L_slow) / L_slow
    c_ms: str = "c"  # T_slow_ms - T_fast_ms


def _ensure_np(x: Any) -> np.ndarray:
    if isinstance(x, np.ndarray):
        return x
    return np.asarray(x)


def wilson_ci95(k: int, n: int, *, alpha: float = 0.05) -> tuple[float, float]:
    """
    Two-sided Wilson confidence interval for a Bernoulli rate.
    Returns (lo, hi).
    """

    if n <= 0:
        return 0.0, 0.0
    # z for 1 - alpha/2.
    z = float(NormalDist().inv_cdf(1.0 - float(alpha) / 2.0))
    phat = float(k / n)
    den = 1.0 + (z * z) / n
    center = (phat + (z * z) / (2.0 * n)) / den
    half = (z * math.sqrt((phat * (1.0 - phat) + (z * z) / (4.0 * n)) / n)) / den
    lo = max(0.0, center - half)
    hi = min(1.0, center + half)
    return float(lo), float(hi)


def split_conformal_upper_q(
    *,
    y_cal: np.ndarray,
    yhat_cal: np.ndarray,
    alpha: float,
) -> float:
    """
    One-sided split conformal quantile for an upper bound: y <= yhat + q.

    Uses nonconformity s = max(y - yhat, 0) and the standard (n+1)(1-alpha)/n level
    with "higher" interpolation for finite-sample validity.
    """

    y_cal = _ensure_np(y_cal).astype(np.float64)
    yhat_cal = _ensure_np(yhat_cal).astype(np.float64)
    if y_cal.shape != yhat_cal.shape:
        raise ValueError(f"Shape mismatch: y_cal{y_cal.shape} vs yhat_cal{yhat_cal.shape}")
    s = np.maximum(y_cal - yhat_cal, 0.0)
    n = int(s.size)
    if n <= 0:
        return 0.0
    level = float(np.ceil((n + 1) * (1.0 - float(alpha))) / n)
    level = float(np.clip(level, 0.0, 1.0))
    # NumPy>=1.22 supports `method=`; fall back for older versions.
    try:
        q = float(np.quantile(s, level, method="higher"))
    except TypeError:  # pragma: no cover
        q = float(np.quantile(s, level, interpolation="higher"))
    return q


def derive_q_rel_and_c(
    df: Any,
    *,
    schema: CounterfactualSchema,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Derive q_rel and c from base counterfactual columns.
    Returns (q_rel, c_ms).
    """

    l_fast = _ensure_np(df[schema.l_fast]).astype(np.float64)
    l_slow = _ensure_np(df[schema.l_slow]).astype(np.float64)
    q_rel = (l_fast - l_slow) / np.maximum(l_slow, 1e-6)
    t_fast = _ensure_np(df[schema.t_fast_ms]).astype(np.float64)
    t_slow = _ensure_np(df[schema.t_slow_ms]).astype(np.float64)
    c_ms = t_slow - t_fast
    return q_rel.astype(np.float64), c_ms.astype(np.float64)


def router_metrics(
    df: Any,
    *,
    use_fast: np.ndarray,
    protocol: RiskBudgetProtocol,
    schema: CounterfactualSchema,
    t_ref: float | None = None,
    beta: float | None = None,
) -> dict[str, float | int | list[float]]:
    """
    Compute basic metrics under the frozen protocol semantics:
    - delta_l_rel uses slow as reference.
    - violation event: (use_fast == True) & (delta_l_rel > epsilon_rel).

    If t_ref and beta are provided, also reports J = T/T_ref + beta*max(delta_l_rel,0).
    """

    use_fast = _ensure_np(use_fast).astype(bool)
    l_slow = _ensure_np(df[schema.l_slow]).astype(np.float64)
    l = np.where(use_fast, _ensure_np(df[schema.l_fast]).astype(np.float64), l_slow)
    t = np.where(
        use_fast,
        _ensure_np(df[schema.t_fast_ms]).astype(np.float64),
        _ensure_np(df[schema.t_slow_ms]).astype(np.float64),
    )
    drel = (l - l_slow) / np.maximum(l_slow, 1e-6)
    vio = (drel > float(protocol.epsilon_rel)) & use_fast

    k = int(np.sum(vio))
    n = int(len(vio))
    ci_lo, ci_hi = wilson_ci95(k, n, alpha=float(protocol.alpha))
    out: dict[str, float | int | list[float]] = {
        "num_cases": n,
        "fast_ratio": float(np.mean(use_fast)) if n > 0 else 0.0,
        "avg_latency_ms": float(np.mean(t)) if n > 0 else 0.0,
        "avg_delta_l_rel": float(np.mean(drel)) if n > 0 else 0.0,
        "violation_rate": float(np.mean(vio)) if n > 0 else 0.0,
        "violation_count": k,
        "violation_rate_ci95": [float(ci_lo), float(ci_hi)],
    }

    if (t_ref is not None) and (beta is not None):
        t_ref = float(max(float(t_ref), 1e-9))
        beta = float(beta)
        j = t / t_ref + beta * np.maximum(drel, 0.0)
        j_oracle = np.minimum(
            (_ensure_np(df[schema.t_fast_ms]).astype(np.float64) / t_ref + beta * np.maximum(derive_q_rel_and_c(df, schema=schema)[0], 0.0)),
            (_ensure_np(df[schema.t_slow_ms]).astype(np.float64) / t_ref),
        )
        j_mean = float(np.mean(j)) if n > 0 else 0.0
        j_oracle_mean = float(np.mean(j_oracle)) if n > 0 else 0.0
        og = (j_mean - j_oracle_mean) / max(abs(j_oracle_mean), 1e-9)
        out.update(
            {
                "t_ref": float(t_ref),
                "beta": float(beta),
                "J_mean": float(j_mean),
                "J_oracle_mean": float(j_oracle_mean),
                "oracle_gap": float(og),
            }
        )
    return out


class RouterMethod(Protocol):
    def fit(self, calib_df: Any) -> "RouterMethod": ...

    def route(self, df: Any) -> tuple[np.ndarray, dict[str, Any]]: ...


def choose_tau_by_topk(score: np.ndarray, *, k_slow: int) -> float:
    score = _ensure_np(score).astype(np.float64)
    if k_slow <= 0:
        return float(np.max(score) + 1e-12)
    if k_slow >= int(score.size):
        return float(np.min(score) - 1e-12)
    ord_desc = np.argsort(score)[::-1]
    hi = float(score[ord_desc[k_slow - 1]])
    lo = float(score[ord_desc[k_slow]])
    return float((hi + lo) * 0.5)


@dataclass(frozen=True)
class ConformalStageConfig:
    protocol: RiskBudgetProtocol = RiskBudgetProtocol()
    schema: CounterfactualSchema = CounterfactualSchema()

    group_values: tuple[str, ...] = ("easy", "medium", "hard")

    # Split conformal coverage (one-sided upper bound): y <= yhat + q, with prob >= 1-alpha_conformal.
    alpha_conformal: float = 0.65

    # Score hyperparameters (kept for compatibility with existing router policy artifact semantics).
    score_power_a: float = 1.0
    score_cost_power_b: float = 1.0

    # Features: numeric + categorical (dummy-encoded).
    feature_num: tuple[str, ...] = (
        "line_block_ratio",
        "local_occ_ratio",
        "global_occ_ratio",
        "distance_ratio",
        "complexity_score",
        "los_clear",
        "L_fast",
        "T_fast_ms",
        "search_fast_ms",
        "path_len_fast",
    )
    # IMPORTANT(validity): avoid dataset identifiers (source_dataset/scenario/map_id) and split-derived flags.
    feature_cat: tuple[str, ...] = ("difficulty",)


@dataclass(frozen=True)
class ProbeFlipStageConfig:
    schema: CounterfactualSchema = CounterfactualSchema()
    group_values: tuple[str, ...] = ("easy", "medium", "hard")

    probe_feature_num: tuple[str, ...] = (
        "probe_success",
        "probe_expansions",
        "probe_runtime_ms",
        "probe_expansion_ratio",
        "probe_h_drop_ratio",
        "probe_progress_per_exp",
        "probe_open_growth",
        "probe_branching",
        "probe_improve_rate",
        "probe_bottleneck_rate",
        "probe_deadend_rate",
        "line_block_ratio",
        "local_occ_ratio",
        "global_occ_ratio",
        "distance_ratio",
        "complexity_score",
        "L_fast",
        "T_fast_ms",
        "search_fast_ms",
        "path_len_fast",
    )
    # IMPORTANT(validity): avoid dataset identifiers (source_dataset/scenario/map_id) and split-derived flags.
    probe_feature_cat: tuple[str, ...] = ("difficulty",)

    gain_power: float = 1.0
    w_hard: float = 0.5
    w_bottleneck: float = 0.0
    w_stall: float = 0.0


def _pd_get_dummies(df: Any, *, num_cols: tuple[str, ...], cat_cols: tuple[str, ...]):
    try:
        import pandas as pd  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("Missing dependency: pandas") from exc
    return pd.get_dummies(df[list(num_cols) + list(cat_cols)], columns=list(cat_cols), drop_first=False)


def _align_dummy_columns(x_ref: Any, x_new: Any):
    # x_ref/x_new are pandas DataFrames.
    return x_new.reindex(columns=x_ref.columns, fill_value=0)


def _as_float_array(v: Any) -> np.ndarray:
    return _ensure_np(v).astype(np.float64)


def _as_bool_array(v: Any) -> np.ndarray:
    return _ensure_np(v).astype(bool)


def _auto_k_by_group_under_risk(
    df: Any,
    *,
    score: np.ndarray,
    group_col: str,
    group_values: tuple[str, ...],
    y_violation: np.ndarray,
    risk_alpha: float,
) -> dict[str, int]:
    """
    Pick minimal k_slow per group such that Wilson upper bound on violation rate <= risk_alpha.

    This is a simple, robust demo-grade rule. Production policies may choose k differently (e.g., to optimize J).
    """

    score = _as_float_array(score)
    y_violation = _as_bool_array(y_violation)
    groups = _ensure_np(df[group_col]).astype(str)
    out: dict[str, int] = {}
    for g in group_values:
        ids = np.where(groups == str(g))[0]
        if ids.size <= 0:
            out[str(g)] = 0
            continue
        ord_desc_pos = np.argsort(score[ids])[::-1]  # positions within `ids`
        use_fast = np.ones(ids.size, dtype=bool)
        k_slow = 0
        while True:
            vio = y_violation[ids] & use_fast
            k = int(np.sum(vio))
            n = int(vio.size)
            _, ci_hi = wilson_ci95(k, n, alpha=float(risk_alpha))
            if ci_hi <= float(risk_alpha) + 1e-12:
                break
            if k_slow >= int(ord_desc_pos.size):
                k_slow = int(ord_desc_pos.size)
                break
            use_fast[ord_desc_pos[k_slow]] = False
            k_slow += 1
        out[str(g)] = int(k_slow)
    return out


class ConformalStageRouter:
    """
    Stage-1 router: learn a score from static features, then apply a per-group threshold.

    This class is intentionally lightweight and does not depend on the closed-loop planner.
    """

    def __init__(
        self,
        *,
        cfg: ConformalStageConfig,
        violation_clf: Any,
        cost_reg: Any,
        k_slow_by_group: dict[str, int] | None = None,
        tau_by_group: dict[str, float] | None = None,
        auto_select_k_by_risk: bool = False,
    ) -> None:
        self.cfg = cfg
        self.violation_clf = violation_clf
        self.cost_reg = cost_reg
        self.k_slow_by_group = k_slow_by_group
        self.tau_by_group = tau_by_group
        self.auto_select_k_by_risk = bool(auto_select_k_by_risk)

        self._x_ref = None
        self._q_by_group: dict[str, float] = {}

    def _build_x(self, df: Any):
        x = _pd_get_dummies(df, num_cols=self.cfg.feature_num, cat_cols=self.cfg.feature_cat)
        if self._x_ref is None:
            self._x_ref = x
            return x
        return _align_dummy_columns(self._x_ref, x)

    def fit(self, calib_df: Any) -> "ConformalStageRouter":
        protocol = self.cfg.protocol
        schema = self.cfg.schema
        x_cal = self._build_x(calib_df)

        # Labels for violation under fast.
        if schema.q_rel in calib_df:
            q_rel = _as_float_array(calib_df[schema.q_rel])
        else:
            q_rel, _ = derive_q_rel_and_c(calib_df, schema=schema)
        y_cal = (q_rel > float(protocol.epsilon_rel)).astype(np.float64)

        # Fit models.
        self.violation_clf.fit(x_cal, y_cal)
        p_hat = _as_float_array(self.violation_clf.predict_proba(x_cal)[:, 1])

        self.cost_reg.fit(x_cal, _as_float_array(calib_df.get(schema.c_ms, derive_q_rel_and_c(calib_df, schema=schema)[1])))

        # Split conformal offsets per group.
        groups = _ensure_np(calib_df[schema.group]).astype(str)
        self._q_by_group = {}
        for g in self.cfg.group_values:
            mask = groups == str(g)
            if int(np.sum(mask)) <= 0:
                self._q_by_group[str(g)] = 0.0
                continue
            q = split_conformal_upper_q(y_cal=y_cal[mask], yhat_cal=p_hat[mask], alpha=float(self.cfg.alpha_conformal))
            self._q_by_group[str(g)] = float(q)

        # Choose tau thresholds from calib, if requested.
        p_upper = np.clip(p_hat + np.array([self._q_by_group.get(str(g), 0.0) for g in groups], dtype=np.float64), 0.0, 1.0)
        c_hat = np.clip(_as_float_array(self.cost_reg.predict(x_cal)), 1e-6, None)
        c_ref = float(max(np.median(c_hat), 1e-6))
        c_norm = np.clip(c_hat / c_ref, 1e-6, None)

        a = float(self.cfg.score_power_a)
        b = float(self.cfg.score_cost_power_b)
        score = (np.clip(p_upper, 1e-9, 1.0) ** a) / (c_norm**b)

        if self.tau_by_group is not None:
            return self

        if (self.k_slow_by_group is None) and self.auto_select_k_by_risk:
            # Auto pick k per group to satisfy risk budget (demo-grade).
            y_vio = y_cal.astype(bool)
            self.k_slow_by_group = _auto_k_by_group_under_risk(
                calib_df,
                score=score,
                group_col=schema.group,
                group_values=self.cfg.group_values,
                y_violation=y_vio,
                risk_alpha=float(protocol.alpha),
            )

        if self.k_slow_by_group is None:
            raise ValueError("Missing selection rule: provide tau_by_group or k_slow_by_group, or enable auto_select_k_by_risk.")

        self.tau_by_group = {}
        for g in self.cfg.group_values:
            ids = np.where(groups == str(g))[0]
            k_slow = int(self.k_slow_by_group.get(str(g), 0))
            self.tau_by_group[str(g)] = choose_tau_by_topk(score[ids], k_slow=k_slow) if ids.size > 0 else float("inf")
        return self

    def route(self, df: Any) -> tuple[np.ndarray, dict[str, Any]]:
        if self.tau_by_group is None:
            raise RuntimeError("Call fit() first.")
        schema = self.cfg.schema

        x = self._build_x(df)
        p_hat = _as_float_array(self.violation_clf.predict_proba(x)[:, 1])
        groups = _ensure_np(df[schema.group]).astype(str)
        q = np.array([self._q_by_group.get(str(g), 0.0) for g in groups], dtype=np.float64)
        p_upper = np.clip(p_hat + q, 0.0, 1.0)

        c_hat = np.clip(_as_float_array(self.cost_reg.predict(x)), 1e-6, None)
        c_ref = float(max(np.median(c_hat), 1e-6))
        c_norm = np.clip(c_hat / c_ref, 1e-6, None)

        a = float(self.cfg.score_power_a)
        b = float(self.cfg.score_cost_power_b)
        score = (np.clip(p_upper, 1e-9, 1.0) ** a) / (c_norm**b)

        tau = np.array([float(self.tau_by_group.get(str(g), float("inf"))) for g in groups], dtype=np.float64)
        use_fast = score <= tau
        meta = {
            "p_hat": p_hat,
            "p_upper": p_upper,
            "c_hat_ms": c_hat,
            "score": score,
            "tau_by_group": dict(self.tau_by_group),
            "q_by_group": dict(self._q_by_group),
        }
        return use_fast.astype(bool), meta


class ProbeFlipRouter:
    """
    Stage-2 router: starting from a base route (conformal stage), run a learned probe score and flip some fast to slow.

    Safety note: if flips are only fast->slow, violation probability is monotone non-increasing.
    """

    def __init__(
        self,
        *,
        cfg: ProbeFlipStageConfig,
        base: ConformalStageRouter,
        gain_reg: Any,
        k_flip_to_slow_by_group: dict[str, int] | None = None,
        tau_probe_by_group: dict[str, float] | None = None,
    ) -> None:
        self.cfg = cfg
        self.base = base
        self.gain_reg = gain_reg
        self.k_flip_to_slow_by_group = k_flip_to_slow_by_group
        self.tau_probe_by_group = tau_probe_by_group
        self._x_ref = None

    def _build_x(self, df: Any):
        x = _pd_get_dummies(df, num_cols=self.cfg.probe_feature_num, cat_cols=self.cfg.probe_feature_cat)
        if self._x_ref is None:
            self._x_ref = x
            return x
        return _align_dummy_columns(self._x_ref, x)

    def fit(self, calib_df: Any) -> "ProbeFlipRouter":
        if self.k_flip_to_slow_by_group is None and self.tau_probe_by_group is None:
            raise ValueError("Provide k_flip_to_slow_by_group or tau_probe_by_group for the probe stage.")
        schema = self.cfg.schema
        base_use_fast, _ = self.base.route(calib_df)

        # Gain target: J_gain_pos = max(J_fast - J_slow, 0).
        q_rel, _ = derive_q_rel_and_c(calib_df, schema=schema)
        # Choose t_ref,beta as in the strict scripts: t_ref = median(T_slow), beta ~ median(T_slow/T_ref)/median(q_pos).
        t_ref = float(max(np.median(_as_float_array(calib_df[schema.t_slow_ms])), 1e-9))
        q_pos = np.maximum(q_rel, 0.0)
        nz = q_pos[q_pos > 1e-9]
        q_med = float(np.median(nz)) if nz.size > 0 else 1.0
        beta = float(np.clip(np.median(_as_float_array(calib_df[schema.t_slow_ms]) / t_ref) / max(q_med, 1e-9), 1e-3, 200.0))
        j_fast = _as_float_array(calib_df[schema.t_fast_ms]) / t_ref + beta * np.maximum(q_rel, 0.0)
        j_slow = _as_float_array(calib_df[schema.t_slow_ms]) / t_ref
        y_gain = np.maximum(j_fast - j_slow, 0.0)

        x_cal = self._build_x(calib_df)
        self.gain_reg.fit(x_cal, y_gain.astype(np.float64))
        pred_gain = np.clip(_as_float_array(self.gain_reg.predict(x_cal)), 0.0, None)

        # Probe score: (pred_gain^gain_power) * (1 + w_hard*I_hard + w_bottle*bottleneck + w_stall*stall).
        hard = (_ensure_np(calib_df[schema.group]).astype(str) == "hard").astype(np.float64)
        bottle = np.clip(_as_float_array(calib_df.get("probe_bottleneck_rate", np.zeros(len(calib_df)))), 0.0, 1.0)
        stall = np.clip(1.0 - _as_float_array(calib_df.get("probe_h_drop_ratio", np.ones(len(calib_df)))), 0.0, 1.0)
        mult = 1.0 + float(self.cfg.w_hard) * hard + float(self.cfg.w_bottleneck) * bottle + float(self.cfg.w_stall) * stall
        score = (pred_gain ** float(self.cfg.gain_power)) * mult
        score = score + np.arange(score.size, dtype=np.float64) * 1e-12

        if self.tau_probe_by_group is None:
            groups = _ensure_np(calib_df[schema.group]).astype(str)
            self.tau_probe_by_group = {}
            for g in self.cfg.group_values:
                ids = np.where((groups == str(g)) & base_use_fast)[0]
                k = int(self.k_flip_to_slow_by_group.get(str(g), 0)) if self.k_flip_to_slow_by_group is not None else 0
                self.tau_probe_by_group[str(g)] = choose_tau_by_topk(score[ids], k_slow=k) if ids.size > 0 else float("inf")
        return self

    def route(self, df: Any) -> tuple[np.ndarray, dict[str, Any]]:
        if self.tau_probe_by_group is None:
            raise RuntimeError("Call fit() first.")
        schema = self.cfg.schema

        base_use_fast, base_meta = self.base.route(df)
        x = self._build_x(df)
        pred_gain = np.clip(_as_float_array(self.gain_reg.predict(x)), 0.0, None)

        hard = (_ensure_np(df[schema.group]).astype(str) == "hard").astype(np.float64)
        bottle = np.clip(_as_float_array(df.get("probe_bottleneck_rate", np.zeros(len(df)))), 0.0, 1.0)
        stall = np.clip(1.0 - _as_float_array(df.get("probe_h_drop_ratio", np.ones(len(df)))), 0.0, 1.0)
        mult = 1.0 + float(self.cfg.w_hard) * hard + float(self.cfg.w_bottleneck) * bottle + float(self.cfg.w_stall) * stall
        score = (pred_gain ** float(self.cfg.gain_power)) * mult

        groups = _ensure_np(df[schema.group]).astype(str)
        tau = np.array([float(self.tau_probe_by_group.get(str(g), float("inf"))) for g in groups], dtype=np.float64)
        flip_to_slow = (score > tau) & base_use_fast
        use_fast = base_use_fast & (~flip_to_slow)
        meta = {
            "base": base_meta,
            "pred_gain": pred_gain,
            "probe_score": score,
            "tau_probe_by_group": dict(self.tau_probe_by_group),
            "probe_flipped_count": int(np.sum(flip_to_slow)),
        }
        return use_fast.astype(bool), meta
