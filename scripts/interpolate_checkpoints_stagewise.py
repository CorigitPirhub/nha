from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
from typing import Any

import torch

SHALLOW_PREFIXES = ("inc.", "down1.")
DEEP_PREFIXES = ("down2.", "down3.", "context_dilated.", "context_ppm.")
DECODER_PREFIXES = ("up1_conv.", "up2_conv.", "up3_conv.")
HEAD_PREFIXES = ("out.",)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Stage-wise interpolation between two model checkpoints.")
    p.add_argument("--ckpt-old", type=Path, required=True, help="Old/base checkpoint path.")
    p.add_argument("--ckpt-new", type=Path, required=True, help="New checkpoint path.")
    p.add_argument("--out", type=Path, required=True, help="Output checkpoint path.")

    p.add_argument("--alpha-default", type=float, default=0.0, help="Fallback alpha for unmatched keys.")
    p.add_argument("--alpha-shallow", type=float, default=None, help="Alpha for shallow encoder (inc/down1).")
    p.add_argument("--alpha-deep", type=float, default=None, help="Alpha for deep/context encoder blocks.")
    p.add_argument("--alpha-decoder", type=float, default=None, help="Alpha for decoder blocks.")
    p.add_argument("--alpha-head", type=float, default=None, help="Alpha for output head.")

    p.add_argument(
        "--bn-stat-source",
        type=str,
        default="blend",
        choices=("blend", "old", "new"),
        help="Source for BatchNorm running stats (running_mean/running_var/num_batches_tracked).",
    )
    p.add_argument(
        "--prefer-new-for-nonfloat",
        action="store_true",
        default=False,
        help="For non-float tensors with same shape, use new tensor regardless of alpha.",
    )
    return p.parse_args()


def _extract_state(payload: Any) -> tuple[str, dict[str, torch.Tensor]]:
    if isinstance(payload, dict):
        for key in ("model_state", "model_state_dict", "state_dict"):
            maybe = payload.get(key)
            if isinstance(maybe, dict) and all(isinstance(v, torch.Tensor) for v in maybe.values()):
                return key, maybe
        if all(isinstance(v, torch.Tensor) for v in payload.values()):
            return "__raw_state_dict__", payload
    raise RuntimeError("Unsupported checkpoint format: expected model_state/model_state_dict/state_dict or raw state_dict.")


def _stage_for_key(key: str) -> str:
    if key.startswith(SHALLOW_PREFIXES):
        return "shallow"
    if key.startswith(DEEP_PREFIXES):
        return "deep"
    if key.startswith(DECODER_PREFIXES):
        return "decoder"
    if key.startswith(HEAD_PREFIXES):
        return "head"
    return "default"


def _is_bn_stat(key: str) -> bool:
    return (
        key.endswith(".running_mean")
        or key.endswith(".running_var")
        or key.endswith(".num_batches_tracked")
    )


def _blend_tensor(old_t: torch.Tensor, new_t: torch.Tensor, alpha: float, prefer_new_for_nonfloat: bool) -> torch.Tensor:
    if old_t.dtype.is_floating_point and new_t.dtype.is_floating_point:
        out = old_t.to(torch.float32).mul(1.0 - alpha).add(new_t.to(torch.float32), alpha=float(alpha))
        return out.to(dtype=new_t.dtype)
    if prefer_new_for_nonfloat:
        return new_t.clone()
    if alpha >= 0.5:
        return new_t.clone()
    return old_t.clone()


def _validate_alpha(name: str, value: float) -> None:
    if value < 0.0 or value > 1.0:
        raise ValueError(f"{name} must be in [0,1], got {value}")


def _resolve_alphas(args: argparse.Namespace) -> dict[str, float]:
    alpha_default = float(args.alpha_default)
    _validate_alpha("--alpha-default", alpha_default)

    stage_alphas: dict[str, float] = {
        "default": alpha_default,
        "shallow": alpha_default if args.alpha_shallow is None else float(args.alpha_shallow),
        "deep": alpha_default if args.alpha_deep is None else float(args.alpha_deep),
        "decoder": alpha_default if args.alpha_decoder is None else float(args.alpha_decoder),
        "head": alpha_default if args.alpha_head is None else float(args.alpha_head),
    }
    for k, v in stage_alphas.items():
        _validate_alpha(f"alpha[{k}]", v)
    return stage_alphas


def _assign_state(out_payload: Any, state_key: str, state: dict[str, torch.Tensor]) -> Any:
    if state_key == "__raw_state_dict__":
        return state
    out = deepcopy(out_payload)
    out[state_key] = state
    return out


def main() -> None:
    args = _parse_args()
    stage_alphas = _resolve_alphas(args)

    old_payload = torch.load(args.ckpt_old, map_location="cpu", weights_only=False)
    new_payload = torch.load(args.ckpt_new, map_location="cpu", weights_only=False)
    old_state_key, old_state = _extract_state(old_payload)
    new_state_key, new_state = _extract_state(new_payload)

    # Use the old checkpoint state location to resolve source tensors; write into new payload layout.
    _ = old_state_key

    blended_state: dict[str, torch.Tensor] = {}
    matched = 0
    missing_old = 0
    shape_mismatch = 0
    bn_overrides = 0
    stage_counts = {k: 0 for k in ("shallow", "deep", "decoder", "head", "default")}

    bn_stat_source = str(args.bn_stat_source).lower()
    prefer_new_nonfloat = bool(args.prefer_new_for_nonfloat)

    for k, new_v in new_state.items():
        old_v = old_state.get(k)
        if old_v is None:
            blended_state[k] = new_v.clone()
            missing_old += 1
            continue
        if tuple(old_v.shape) != tuple(new_v.shape):
            blended_state[k] = new_v.clone()
            shape_mismatch += 1
            continue

        stage = _stage_for_key(k)
        alpha = stage_alphas[stage]

        if _is_bn_stat(k) and bn_stat_source in {"old", "new"}:
            blended_state[k] = old_v.clone() if bn_stat_source == "old" else new_v.clone()
            bn_overrides += 1
        else:
            blended_state[k] = _blend_tensor(old_v, new_v, alpha=alpha, prefer_new_for_nonfloat=prefer_new_nonfloat)
        matched += 1
        stage_counts[stage] += 1

    out_payload = _assign_state(new_payload, new_state_key, blended_state)
    if isinstance(out_payload, dict):
        out_payload["interpolation_meta"] = {
            "mode": "stagewise",
            "ckpt_old": str(args.ckpt_old),
            "ckpt_new": str(args.ckpt_new),
            "stage_alphas": {k: float(v) for k, v in stage_alphas.items()},
            "bn_stat_source": bn_stat_source,
            "matched": int(matched),
            "missing_old": int(missing_old),
            "shape_mismatch": int(shape_mismatch),
            "bn_overrides": int(bn_overrides),
            "stage_counts": {k: int(v) for k, v in stage_counts.items()},
        }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(out_payload, args.out)
    print(
        f"[interp-stage] wrote={args.out} matched={matched} missing_old={missing_old} "
        f"shape_mismatch={shape_mismatch} bn_overrides={bn_overrides} alphas={stage_alphas}"
    )


if __name__ == "__main__":
    main()
