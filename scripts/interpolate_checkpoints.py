from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
from typing import Any

import torch


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Linear interpolation between two model checkpoints.")
    p.add_argument("--ckpt-old", type=Path, required=True, help="Old/base checkpoint path.")
    p.add_argument("--ckpt-new", type=Path, required=True, help="New checkpoint path.")
    p.add_argument("--alpha", type=float, required=True, help="Interpolation weight for new checkpoint in [0,1].")
    p.add_argument("--out", type=Path, required=True, help="Output checkpoint path.")
    p.add_argument(
        "--prefer-new-for-nonfloat",
        action="store_true",
        default=False,
        help="For non-float tensors with same shape, use new tensor regardless of alpha.",
    )
    return p.parse_args()


def _extract_state(payload: Any) -> dict[str, torch.Tensor]:
    if isinstance(payload, dict) and "model_state" in payload and isinstance(payload["model_state"], dict):
        return payload["model_state"]
    if isinstance(payload, dict):
        # Raw state_dict-like checkpoint.
        if all(isinstance(v, torch.Tensor) for v in payload.values()):
            return payload
    raise RuntimeError("Unsupported checkpoint format: expected dict with 'model_state' or raw state_dict.")


def _blend_tensor(
    old_t: torch.Tensor,
    new_t: torch.Tensor,
    alpha: float,
    prefer_new_for_nonfloat: bool,
) -> torch.Tensor:
    if old_t.dtype.is_floating_point and new_t.dtype.is_floating_point:
        out = old_t.to(torch.float32).mul(1.0 - alpha).add(new_t.to(torch.float32), alpha=float(alpha))
        return out.to(dtype=new_t.dtype)
    if prefer_new_for_nonfloat:
        return new_t.clone()
    if alpha >= 0.5:
        return new_t.clone()
    return old_t.clone()


def main() -> None:
    args = _parse_args()
    alpha = float(args.alpha)
    if alpha < 0.0 or alpha > 1.0:
        raise ValueError(f"--alpha must be in [0,1], got {alpha}")

    old_payload = torch.load(args.ckpt_old, map_location="cpu", weights_only=False)
    new_payload = torch.load(args.ckpt_new, map_location="cpu", weights_only=False)
    old_state = _extract_state(old_payload)
    new_state = _extract_state(new_payload)

    blended_state: dict[str, torch.Tensor] = {}
    matched = 0
    missing_old = 0
    shape_mismatch = 0

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
        blended_state[k] = _blend_tensor(
            old_t=old_v,
            new_t=new_v,
            alpha=alpha,
            prefer_new_for_nonfloat=bool(args.prefer_new_for_nonfloat),
        )
        matched += 1

    out_payload: Any
    if isinstance(new_payload, dict):
        out_payload = deepcopy(new_payload)
        out_payload["model_state"] = blended_state
        out_payload["interpolation_meta"] = {
            "ckpt_old": str(args.ckpt_old),
            "ckpt_new": str(args.ckpt_new),
            "alpha_new": alpha,
            "alpha_old": 1.0 - alpha,
            "matched": int(matched),
            "missing_old": int(missing_old),
            "shape_mismatch": int(shape_mismatch),
        }
    else:
        out_payload = {"model_state": blended_state}

    args.out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(out_payload, args.out)
    print(
        f"[interp] wrote {args.out} alpha={alpha:.4f} matched={matched} "
        f"missing_old={missing_old} shape_mismatch={shape_mismatch}"
    )


if __name__ == "__main__":
    main()

