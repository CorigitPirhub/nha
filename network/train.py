from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import torch
from torch.utils.data import DataLoader

from config import ExperimentConfig
from network.dataset import HeuristicFieldDataset
from network.model import build_model


def _masked_loss(
    pred: torch.Tensor,
    target: torch.Tensor,
    mask: torch.Tensor,
    loss_weight: torch.Tensor,
    sample_weight: torch.Tensor | None,
    underestimation_weight: float,
    hard_mask: torch.Tensor | None = None,
    standard_mask: torch.Tensor | None = None,
    hard_underestimation_weight: float | None = None,
    hard_overestimation_weight: float = 0.0,
    narrow_mask: torch.Tensor | None = None,
    narrow_overestimation_weight: float = 0.0,
    temporal_steps: int = 1,
    yaw_bins: int | None = None,
    temporal_lambda: float = 0.1,
    hard_rank_lambda: float = 0.0,
    hard_rank_topk: int = 64,
    hard_rank_margin: float = 0.01,
    gradient_struct_lambda: float = 0.0,
    laplacian_struct_lambda: float = 0.0,
    local_rank_lambda: float = 0.0,
    local_rank_margin: float = 0.01,
    local_rank_delta_threshold: float = 0.005,
    local_rank_weight_power: float = 1.0,
    grad_dir_lambda: float = 0.0,
    grad_dir_min_mag: float = 0.01,
    local_prob_rank_lambda: float = 0.0,
    local_prob_rank_tau: float = 0.02,
    local_prob_rank_delta_threshold: float = 0.003,
    local_prob_rank_focus_quantile: float = 0.7,
    local_prob_rank_weight_power: float = 1.0,
    local_prob_rank_hard_only: bool = True,
    local_prob_rank_narrow_boost: float = 0.0,
    global_rank_lambda: float = 0.0,
    global_rank_pairs: int = 96,
    global_rank_tau: float = 0.04,
    global_rank_top_quantile: float = 0.85,
    global_rank_bottom_quantile: float = 0.25,
    global_rank_hard_only: bool = True,
    global_rank_narrow_boost: float = 0.0,
    distill_target: torch.Tensor | None = None,
    distill_lambda: float = 0.0,
    distill_huber_delta: float = 0.02,
    distill_focus_quantile: float = 0.0,
    distill_hard_only: bool = False,
    distill_narrow_boost: float = 0.0,
    distill_under_lambda: float = 0.0,
) -> torch.Tensor:
    err = pred - target
    sq = err**2
    under = (err < 0.0).to(pred.dtype)
    under_weight = torch.full_like(err, float(max(underestimation_weight, 1e-3)))
    if hard_mask is not None and hard_underestimation_weight is not None:
        hm = hard_mask.to(pred.dtype).view(-1, 1, 1, 1)
        hw = float(max(hard_underestimation_weight, 1e-3))
        under_weight = under_weight * (1.0 - hm) + hw * hm
    asym_scale = 1.0 + (under_weight - 1.0) * under
    if standard_mask is not None:
        sm = standard_mask.to(pred.dtype).view(-1, 1, 1, 1)
        # Standard benchmark samples use symmetric MSE only.
        asym_scale = asym_scale * (1.0 - sm) + sm
    asym = sq * asym_scale
    w = mask * loss_weight
    if sample_weight is not None:
        w = w * sample_weight.to(pred.dtype).view(-1, 1, 1, 1)
    denom = w.sum().clamp_min(1.0)
    base_loss = (asym * w).sum() / denom

    if float(hard_overestimation_weight) > 0.0:
        over = torch.relu(err)
        ow = w
        if hard_mask is not None:
            ow = ow * hard_mask.to(pred.dtype).view(-1, 1, 1, 1)
        oden = ow.sum().clamp_min(1.0)
        base_loss = base_loss + float(hard_overestimation_weight) * ((over * ow).sum() / oden)

    if float(narrow_overestimation_weight) > 0.0 and narrow_mask is not None:
        nm = narrow_mask.to(pred.dtype)
        if nm.ndim == 3:
            nm = nm.unsqueeze(1)
        if nm.shape[1] == 1 and pred.shape[1] != 1:
            nm = nm.expand(-1, pred.shape[1], -1, -1)
        ow_n = w * nm
        if standard_mask is not None:
            ow_n = ow_n * (1.0 - standard_mask.to(pred.dtype).view(-1, 1, 1, 1))
        oden_n = ow_n.sum().clamp_min(1.0)
        base_loss = base_loss + float(narrow_overestimation_weight) * ((torch.relu(err) * ow_n).sum() / oden_n)

    total_loss = base_loss

    yb = int(yaw_bins) if yaw_bins is not None else int(pred.shape[1])
    t_steps = int(max(temporal_steps, 1))
    if float(temporal_lambda) > 0.0 and t_steps > 1 and yb > 0 and pred.shape[1] == t_steps * yb:
        bsz, _, h, w2 = pred.shape
        pred_t = pred.view(bsz, t_steps, yb, h, w2)
        mask_t = mask.view(bsz, t_steps, yb, h, w2)
        temporal_mask = (mask_t[:, 1:] * mask_t[:, :-1]).to(pred.dtype)
        if standard_mask is not None:
            temporal_mask = temporal_mask * (1.0 - standard_mask.to(pred.dtype).view(-1, 1, 1, 1, 1))
        if sample_weight is not None:
            temporal_mask = temporal_mask * sample_weight.to(pred.dtype).view(-1, 1, 1, 1, 1)
        temporal_diff = torch.abs(pred_t[:, 1:] - pred_t[:, :-1])
        temporal_denom = temporal_mask.sum().clamp_min(1.0)
        temporal_loss = (temporal_diff * temporal_mask).sum() / temporal_denom
        total_loss = total_loss + float(temporal_lambda) * temporal_loss

    # Search-aware ranking consistency for hard scenes:
    # enforce that states with larger teacher residual keep larger predicted residual.
    if float(hard_rank_lambda) > 0.0 and hard_mask is not None:
        margin = float(max(hard_rank_margin, 0.0))
        rank_terms: list[torch.Tensor] = []
        hard_ids = (hard_mask.to(pred.dtype).view(-1) > 0.5).nonzero(as_tuple=False).view(-1)
        for b in hard_ids:
            valid = (mask[b] > 0.5)
            n_valid = int(valid.sum().item())
            if n_valid < 8:
                continue
            t = target[b][valid]
            p = pred[b][valid]
            if t.numel() < 8:
                continue
            k = int(min(max(int(hard_rank_topk), 2), int(t.numel() // 2)))
            if k < 2:
                continue
            hi = torch.topk(t, k=k, largest=True).indices
            lo = torch.topk(t, k=k, largest=False).indices
            p_hi = p[hi].unsqueeze(1)
            p_lo = p[lo].unsqueeze(0)
            rank_terms.append(torch.relu(margin - (p_hi - p_lo)).mean())
        if rank_terms:
            rank_loss = torch.stack(rank_terms).mean()
            total_loss = total_loss + float(hard_rank_lambda) * rank_loss

    if float(gradient_struct_lambda) > 0.0:
        # Structural consistency: preserve local slope field of teacher cost.
        pdx = pred[..., 1:] - pred[..., :-1]
        tdx = target[..., 1:] - target[..., :-1]
        mdx = (mask[..., 1:] * mask[..., :-1]).to(pred.dtype)
        if sample_weight is not None:
            mdx = mdx * sample_weight.to(pred.dtype).view(-1, 1, 1, 1)
        if standard_mask is not None:
            mdx = mdx * (1.0 - standard_mask.to(pred.dtype).view(-1, 1, 1, 1))
        gdx = (torch.abs(pdx - tdx) * mdx).sum() / mdx.sum().clamp_min(1.0)

        pdy = pred[..., 1:, :] - pred[..., :-1, :]
        tdy = target[..., 1:, :] - target[..., :-1, :]
        mdy = (mask[..., 1:, :] * mask[..., :-1, :]).to(pred.dtype)
        if sample_weight is not None:
            mdy = mdy * sample_weight.to(pred.dtype).view(-1, 1, 1, 1)
        if standard_mask is not None:
            mdy = mdy * (1.0 - standard_mask.to(pred.dtype).view(-1, 1, 1, 1))
        gdy = (torch.abs(pdy - tdy) * mdy).sum() / mdy.sum().clamp_min(1.0)
        total_loss = total_loss + float(gradient_struct_lambda) * (gdx + gdy)

    if float(laplacian_struct_lambda) > 0.0:
        # Propagation-shape consistency using channel-wise Laplacian.
        c = int(pred.shape[1])
        lap_k = pred.new_tensor([[0.0, 1.0, 0.0], [1.0, -4.0, 1.0], [0.0, 1.0, 0.0]]).view(1, 1, 3, 3)
        lap_w = lap_k.repeat(c, 1, 1, 1)
        pl = torch.nn.functional.conv2d(pred, lap_w, padding=1, groups=c)
        tl = torch.nn.functional.conv2d(target, lap_w, padding=1, groups=c)
        ml = mask.to(pred.dtype)
        if sample_weight is not None:
            ml = ml * sample_weight.to(pred.dtype).view(-1, 1, 1, 1)
        if standard_mask is not None:
            ml = ml * (1.0 - standard_mask.to(pred.dtype).view(-1, 1, 1, 1))
        lap_loss = (torch.abs(pl - tl) * ml).sum() / ml.sum().clamp_min(1.0)
        total_loss = total_loss + float(laplacian_struct_lambda) * lap_loss

    # Local ordinal structure: preserve teacher ordering between adjacent cells.
    if float(local_rank_lambda) > 0.0:
        rank_margin = float(max(local_rank_margin, 0.0))
        delta_thr = float(max(local_rank_delta_threshold, 0.0))
        w_pow = float(max(local_rank_weight_power, 0.0))

        def _edge_rank_loss(
            p_d: torch.Tensor,
            t_d: torch.Tensor,
            m_d: torch.Tensor,
        ) -> torch.Tensor:
            abs_t = torch.abs(t_d)
            sel = (abs_t >= delta_thr).to(pred.dtype) * m_d
            if sel.sum() <= 0.0:
                return pred.new_tensor(0.0)
            rank_err = torch.relu(rank_margin - torch.sign(t_d) * p_d)
            if w_pow > 0.0:
                rank_w = torch.pow(torch.clamp(abs_t, min=max(delta_thr, 1e-3)), w_pow)
            else:
                rank_w = torch.ones_like(abs_t, dtype=pred.dtype)
            ww = sel * rank_w
            return (rank_err * ww).sum() / ww.sum().clamp_min(1.0)

        pdx = pred[..., 1:] - pred[..., :-1]
        tdx = target[..., 1:] - target[..., :-1]
        mdx = (mask[..., 1:] * mask[..., :-1]).to(pred.dtype)
        if sample_weight is not None:
            mdx = mdx * sample_weight.to(pred.dtype).view(-1, 1, 1, 1)
        if standard_mask is not None:
            mdx = mdx * (1.0 - standard_mask.to(pred.dtype).view(-1, 1, 1, 1))
        rank_x = _edge_rank_loss(pdx, tdx, mdx)

        pdy = pred[..., 1:, :] - pred[..., :-1, :]
        tdy = target[..., 1:, :] - target[..., :-1, :]
        mdy = (mask[..., 1:, :] * mask[..., :-1, :]).to(pred.dtype)
        if sample_weight is not None:
            mdy = mdy * sample_weight.to(pred.dtype).view(-1, 1, 1, 1)
        if standard_mask is not None:
            mdy = mdy * (1.0 - standard_mask.to(pred.dtype).view(-1, 1, 1, 1))
        rank_y = _edge_rank_loss(pdy, tdy, mdy)

        total_loss = total_loss + float(local_rank_lambda) * (rank_x + rank_y)

    # Gradient direction consistency: match structural flow orientation.
    if float(grad_dir_lambda) > 0.0:
        eps = 1e-6
        pdx = pred[..., :-1, 1:] - pred[..., :-1, :-1]
        pdy = pred[..., 1:, :-1] - pred[..., :-1, :-1]
        tdx = target[..., :-1, 1:] - target[..., :-1, :-1]
        tdy = target[..., 1:, :-1] - target[..., :-1, :-1]

        gm = (
            mask[..., :-1, :-1] * mask[..., :-1, 1:] * mask[..., 1:, :-1]
        ).to(pred.dtype)
        if sample_weight is not None:
            gm = gm * sample_weight.to(pred.dtype).view(-1, 1, 1, 1)
        if standard_mask is not None:
            gm = gm * (1.0 - standard_mask.to(pred.dtype).view(-1, 1, 1, 1))

        t_norm = torch.sqrt(tdx * tdx + tdy * tdy + eps)
        p_norm = torch.sqrt(pdx * pdx + pdy * pdy + eps)
        valid = gm * (t_norm >= float(max(grad_dir_min_mag, 0.0))).to(pred.dtype)
        if valid.sum() > 0.0:
            cos = (pdx * tdx + pdy * tdy) / (p_norm * t_norm + eps)
            cos = torch.clamp(cos, -1.0, 1.0)
            dir_loss = ((1.0 - cos) * valid).sum() / valid.sum().clamp_min(1.0)
            total_loss = total_loss + float(grad_dir_lambda) * dir_loss

    # Confidence-gated local soft ranking:
    # replaces hard-margin ordinal constraints with probabilistic order supervision.
    if float(local_prob_rank_lambda) > 0.0:
        tau = float(max(local_prob_rank_tau, 1e-4))
        delta_thr = float(max(local_prob_rank_delta_threshold, 0.0))
        focus_q = float(np.clip(local_prob_rank_focus_quantile, 0.0, 1.0))
        w_pow = float(max(local_prob_rank_weight_power, 0.0))
        hard_only = bool(local_prob_rank_hard_only)
        narrow_boost = float(max(local_prob_rank_narrow_boost, 0.0))

        nm = None
        if narrow_mask is not None:
            nm = narrow_mask.to(pred.dtype)
            if nm.ndim == 3:
                nm = nm.unsqueeze(1)
            if nm.shape[1] == 1 and pred.shape[1] != 1:
                nm = nm.expand(-1, pred.shape[1], -1, -1)

        hm = hard_mask.to(pred.dtype).view(-1, 1, 1, 1) if hard_mask is not None else None

        def _soft_local_rank_loss(
            p_d: torch.Tensor,
            t_d: torch.Tensor,
            m_d: torch.Tensor,
            t_mid: torch.Tensor,
            n_d: torch.Tensor | None,
        ) -> torch.Tensor:
            ww = m_d
            if hard_only and hm is not None:
                ww = ww * hm

            abs_t = torch.abs(t_d)
            conf = torch.relu(abs_t - delta_thr)
            conf = conf / (conf + float(max(delta_thr, 1e-3)))
            if w_pow != 1.0:
                conf = torch.pow(conf, w_pow)
            ww = ww * conf

            if focus_q > 0.0:
                focused = torch.zeros_like(ww)
                for bi in range(ww.shape[0]):
                    vb = ww[bi] > 0.0
                    if int(vb.sum().item()) < 16:
                        focused[bi] = ww[bi]
                        continue
                    qv = torch.quantile(t_mid[bi][vb].float(), focus_q)
                    focused[bi] = ww[bi] * (t_mid[bi] >= qv.to(t_mid.dtype)).to(pred.dtype)
                ww = focused

            if n_d is not None and narrow_boost > 0.0:
                ww = ww * (1.0 + narrow_boost * n_d)

            den = ww.sum().clamp_min(1.0)
            if float(den.item()) <= 1.0:
                return pred.new_tensor(0.0)

            target_prob = torch.sigmoid(t_d / tau).detach()
            pred_logit = p_d / tau
            bce = torch.nn.functional.binary_cross_entropy_with_logits(pred_logit, target_prob, reduction="none")
            return (bce * ww).sum() / den

        pdx = pred[..., 1:] - pred[..., :-1]
        tdx = target[..., 1:] - target[..., :-1]
        mdx = (mask[..., 1:] * mask[..., :-1]).to(pred.dtype)
        tmx = 0.5 * (target[..., 1:] + target[..., :-1])
        ndx = (nm[..., 1:] * nm[..., :-1]).to(pred.dtype) if nm is not None else None
        if sample_weight is not None:
            mdx = mdx * sample_weight.to(pred.dtype).view(-1, 1, 1, 1)
        if standard_mask is not None:
            mdx = mdx * (1.0 - standard_mask.to(pred.dtype).view(-1, 1, 1, 1))
        loss_x = _soft_local_rank_loss(pdx, tdx, mdx, tmx, ndx)

        pdy = pred[..., 1:, :] - pred[..., :-1, :]
        tdy = target[..., 1:, :] - target[..., :-1, :]
        mdy = (mask[..., 1:, :] * mask[..., :-1, :]).to(pred.dtype)
        tmy = 0.5 * (target[..., 1:, :] + target[..., :-1, :])
        ndy = (nm[..., 1:, :] * nm[..., :-1, :]).to(pred.dtype) if nm is not None else None
        if sample_weight is not None:
            mdy = mdy * sample_weight.to(pred.dtype).view(-1, 1, 1, 1)
        if standard_mask is not None:
            mdy = mdy * (1.0 - standard_mask.to(pred.dtype).view(-1, 1, 1, 1))
        loss_y = _soft_local_rank_loss(pdy, tdy, mdy, tmy, ndy)

        total_loss = total_loss + float(local_prob_rank_lambda) * (loss_x + loss_y)

    # Global quantile contrastive ranking:
    # enforce high-residual regions to remain above low-residual regions at map scale.
    if float(global_rank_lambda) > 0.0:
        tau_g = float(max(global_rank_tau, 1e-4))
        top_q = float(np.clip(global_rank_top_quantile, 0.05, 0.99))
        bot_q = float(np.clip(global_rank_bottom_quantile, 0.0, top_q - 1e-3))
        pair_cap = int(max(global_rank_pairs, 4))
        hard_only = bool(global_rank_hard_only)
        narrow_boost = float(max(global_rank_narrow_boost, 0.0))

        nm = None
        if narrow_mask is not None and narrow_boost > 0.0:
            nm = narrow_mask.to(pred.dtype)
            if nm.ndim == 3:
                nm = nm.unsqueeze(1)
            if nm.shape[1] == 1 and pred.shape[1] != 1:
                nm = nm.expand(-1, pred.shape[1], -1, -1)

        pair_terms: list[torch.Tensor] = []
        for b in range(pred.shape[0]):
            if standard_mask is not None and float(standard_mask[b].item()) > 0.5:
                continue
            if hard_only and hard_mask is not None and float(hard_mask[b].item()) <= 0.5:
                continue

            valid = (mask[b] > 0.5)
            if int(valid.sum().item()) < 64:
                continue
            t = target[b][valid]
            p = pred[b][valid]
            if t.numel() < 64:
                continue

            t32 = t.float()
            q_hi = torch.quantile(t32, top_q)
            q_lo = torch.quantile(t32, bot_q)

            hi = (t >= q_hi.to(t.dtype)).nonzero(as_tuple=False).view(-1)
            lo = (t <= q_lo.to(t.dtype)).nonzero(as_tuple=False).view(-1)
            if hi.numel() < 4 or lo.numel() < 4:
                continue

            hi = hi[torch.argsort(t[hi], descending=True)]
            lo = lo[torch.argsort(t[lo], descending=False)]
            k = int(min(pair_cap, hi.numel(), lo.numel()))
            if k < 4:
                continue

            if hi.numel() > k:
                idx_hi = torch.linspace(0, hi.numel() - 1, steps=k, device=hi.device).long()
                hi = hi[idx_hi]
            else:
                hi = hi[:k]
            if lo.numel() > k:
                idx_lo = torch.linspace(0, lo.numel() - 1, steps=k, device=lo.device).long()
                lo = lo[idx_lo]
            else:
                lo = lo[:k]

            t_gap = t[hi] - t[lo]
            p_gap = p[hi] - p[lo]
            logits = p_gap / tau_g
            target_prob = torch.sigmoid(t_gap / tau_g).detach()
            bce = torch.nn.functional.binary_cross_entropy_with_logits(logits, target_prob, reduction="none")

            gap_w = torch.relu(t_gap - 0.1 * (q_hi.to(t.dtype) - q_lo.to(t.dtype)))
            gap_w = gap_w / gap_w.mean().clamp_min(1e-3)
            if nm is not None:
                nflat = nm[b][valid]
                near = torch.maximum(nflat[hi], nflat[lo])
                gap_w = gap_w * (1.0 + narrow_boost * near)

            pair_terms.append((bce * gap_w).mean())

        if pair_terms:
            total_loss = total_loss + float(global_rank_lambda) * torch.stack(pair_terms).mean()

    # Anti-forgetting distillation anchor:
    # keep student close to a fixed strong residual model while learning new structure.
    if distill_target is not None and float(distill_lambda) > 0.0:
        dm = (mask * loss_weight).to(pred.dtype)
        if sample_weight is not None:
            dm = dm * sample_weight.to(pred.dtype).view(-1, 1, 1, 1)
        if standard_mask is not None:
            dm = dm * (1.0 - standard_mask.to(pred.dtype).view(-1, 1, 1, 1))
        if distill_hard_only and hard_mask is not None:
            dm = dm * hard_mask.to(pred.dtype).view(-1, 1, 1, 1)

        nm = None
        if narrow_mask is not None and float(distill_narrow_boost) > 0.0:
            nm = narrow_mask.to(pred.dtype)
            if nm.ndim == 3:
                nm = nm.unsqueeze(1)
            if nm.shape[1] == 1 and pred.shape[1] != 1:
                nm = nm.expand(-1, pred.shape[1], -1, -1)
            dm = dm * (1.0 + float(distill_narrow_boost) * nm)

        fq = float(np.clip(distill_focus_quantile, 0.0, 1.0))
        if fq > 0.0:
            focused = torch.zeros_like(dm)
            for bi in range(dm.shape[0]):
                vb = dm[bi] > 0.0
                if int(vb.sum().item()) < 16:
                    focused[bi] = dm[bi]
                    continue
                qv = torch.quantile(distill_target[bi][vb].float(), fq)
                focused[bi] = dm[bi] * (distill_target[bi] >= qv.to(distill_target.dtype)).to(pred.dtype)
            dm = focused

        dden = dm.sum().clamp_min(1.0)
        if float(dden.item()) > 1.0:
            delta = float(max(distill_huber_delta, 1e-5))
            distill_elem = torch.nn.functional.smooth_l1_loss(pred, distill_target.detach(), beta=delta, reduction="none")
            distill_loss = (distill_elem * dm).sum() / dden
            total_loss = total_loss + float(distill_lambda) * distill_loss

            if float(distill_under_lambda) > 0.0:
                under = torch.relu(distill_target.detach() - pred)
                under_loss = (under * dm).sum() / dden
                total_loss = total_loss + float(distill_under_lambda) * under_loss

    return total_loss


def _eval(
    model: torch.nn.Module,
    loader: DataLoader,
    device: torch.device,
    underestimation_weight: float,
    hard_underestimation_weight: float | None = None,
    hard_overestimation_weight: float = 0.0,
    narrow_overestimation_weight: float = 0.0,
    hard_rank_lambda: float = 0.0,
    hard_rank_topk: int = 64,
    hard_rank_margin: float = 0.01,
    gradient_struct_lambda: float = 0.0,
    laplacian_struct_lambda: float = 0.0,
    local_rank_lambda: float = 0.0,
    local_rank_margin: float = 0.01,
    local_rank_delta_threshold: float = 0.005,
    local_rank_weight_power: float = 1.0,
    grad_dir_lambda: float = 0.0,
    grad_dir_min_mag: float = 0.01,
    local_prob_rank_lambda: float = 0.0,
    local_prob_rank_tau: float = 0.02,
    local_prob_rank_delta_threshold: float = 0.003,
    local_prob_rank_focus_quantile: float = 0.7,
    local_prob_rank_weight_power: float = 1.0,
    local_prob_rank_hard_only: bool = True,
    local_prob_rank_narrow_boost: float = 0.0,
    global_rank_lambda: float = 0.0,
    global_rank_pairs: int = 96,
    global_rank_tau: float = 0.04,
    global_rank_top_quantile: float = 0.85,
    global_rank_bottom_quantile: float = 0.25,
    global_rank_hard_only: bool = True,
    global_rank_narrow_boost: float = 0.0,
    distill_lambda: float = 0.0,
    distill_huber_delta: float = 0.02,
    distill_focus_quantile: float = 0.0,
    distill_hard_only: bool = False,
    distill_narrow_boost: float = 0.0,
    distill_under_lambda: float = 0.0,
) -> float:
    model.eval()
    total = 0.0
    count = 0
    with torch.no_grad():
        for batch in loader:
            x = batch["input"].to(device, non_blocking=True)
            y = batch["target"].to(device, non_blocking=True)
            m = batch["mask"].to(device, non_blocking=True)
            lw = batch["loss_weight"].to(device, non_blocking=True)
            sw = batch.get("sample_weight")
            if sw is not None:
                sw = sw.to(device, non_blocking=True)
            hm = batch.get("is_hard")
            if hm is not None:
                hm = hm.to(device, non_blocking=True)
            sm = batch.get("is_standard")
            if sm is not None:
                sm = sm.to(device, non_blocking=True)
            nm = batch.get("narrow_mask")
            if nm is not None:
                nm = nm.to(device, non_blocking=True)
            t_steps = int(batch.get("temporal_steps", torch.tensor([1]))[0].item())
            yaw_bins = int(batch.get("yaw_bins", torch.tensor([y.shape[1]]))[0].item())
            pred = model(x)
            loss = _masked_loss(
                pred,
                y,
                m,
                lw,
                sw,
                underestimation_weight=underestimation_weight,
                hard_mask=hm,
                standard_mask=sm,
                hard_underestimation_weight=hard_underestimation_weight,
                hard_overestimation_weight=hard_overestimation_weight,
                narrow_mask=nm,
                narrow_overestimation_weight=narrow_overestimation_weight,
                temporal_steps=t_steps,
                yaw_bins=yaw_bins,
                temporal_lambda=0.1,
                hard_rank_lambda=hard_rank_lambda,
                hard_rank_topk=hard_rank_topk,
                hard_rank_margin=hard_rank_margin,
                gradient_struct_lambda=gradient_struct_lambda,
                laplacian_struct_lambda=laplacian_struct_lambda,
                local_rank_lambda=local_rank_lambda,
                local_rank_margin=local_rank_margin,
                local_rank_delta_threshold=local_rank_delta_threshold,
                local_rank_weight_power=local_rank_weight_power,
                grad_dir_lambda=grad_dir_lambda,
                grad_dir_min_mag=grad_dir_min_mag,
                local_prob_rank_lambda=local_prob_rank_lambda,
                local_prob_rank_tau=local_prob_rank_tau,
                local_prob_rank_delta_threshold=local_prob_rank_delta_threshold,
                local_prob_rank_focus_quantile=local_prob_rank_focus_quantile,
                local_prob_rank_weight_power=local_prob_rank_weight_power,
                local_prob_rank_hard_only=local_prob_rank_hard_only,
                local_prob_rank_narrow_boost=local_prob_rank_narrow_boost,
                global_rank_lambda=global_rank_lambda,
                global_rank_pairs=global_rank_pairs,
                global_rank_tau=global_rank_tau,
                global_rank_top_quantile=global_rank_top_quantile,
                global_rank_bottom_quantile=global_rank_bottom_quantile,
                global_rank_hard_only=global_rank_hard_only,
                global_rank_narrow_boost=global_rank_narrow_boost,
                distill_target=None,
                distill_lambda=distill_lambda,
                distill_huber_delta=distill_huber_delta,
                distill_focus_quantile=distill_focus_quantile,
                distill_hard_only=distill_hard_only,
                distill_narrow_boost=distill_narrow_boost,
                distill_under_lambda=distill_under_lambda,
            )
            total += float(loss.item())
            count += 1
    return total / max(count, 1)


def _load_init_checkpoint(model: torch.nn.Module, init_checkpoint: Path | None) -> None:
    if init_checkpoint is None:
        return
    payload = torch.load(init_checkpoint, map_location="cpu", weights_only=False)
    src = payload.get("model_state", payload) if isinstance(payload, dict) else payload
    if not isinstance(src, dict):
        raise RuntimeError(f"Unsupported checkpoint format: {init_checkpoint}")

    dst = model.state_dict()
    matched = {}
    skipped = 0
    for k, v in src.items():
        if k in dst and tuple(dst[k].shape) == tuple(v.shape):
            matched[k] = v
        else:
            skipped += 1
    dst.update(matched)
    model.load_state_dict(dst, strict=False)
    print(f"[init] loaded {len(matched)} params from {init_checkpoint} (skipped={skipped})")


def train_network(
    cfg: ExperimentConfig,
    train_dir: Path,
    val_dir: Path,
    init_checkpoint: Path | None = None,
) -> Tuple[Path, Dict[str, float]]:
    requested_device = cfg.train.device
    if requested_device.startswith("cuda") and not torch.cuda.is_available():
        print("[warning] CUDA requested but unavailable, fallback to CPU.")
        requested_device = "cpu"
    device = torch.device(requested_device)

    train_ds = HeuristicFieldDataset(
        train_dir,
        gaussian_sigma=cfg.dataset.gaussian_sigma,
        distance_weight_scale_m=cfg.train.distance_weight_scale_m,
        distance_weight_min=cfg.train.distance_weight_min,
        hybrid_obstacle_alpha=cfg.dataset.hybrid_obstacle_alpha,
        hybrid_obstacle_threshold_m=cfg.dataset.hybrid_obstacle_threshold_m,
        prediction_mode=cfg.train.prediction_mode,
        type_c_loss_weight=cfg.train.type_c_loss_weight,
    )
    val_ds = HeuristicFieldDataset(
        val_dir,
        gaussian_sigma=cfg.dataset.gaussian_sigma,
        distance_weight_scale_m=cfg.train.distance_weight_scale_m,
        distance_weight_min=cfg.train.distance_weight_min,
        hybrid_obstacle_alpha=cfg.dataset.hybrid_obstacle_alpha,
        hybrid_obstacle_threshold_m=cfg.dataset.hybrid_obstacle_threshold_m,
        prediction_mode=cfg.train.prediction_mode,
        type_c_loss_weight=cfg.train.type_c_loss_weight,
    )

    out_channels = int(train_ds[0]["target"].shape[0])
    in_channels = int(train_ds[0]["input"].shape[0])
    output_activation = "identity" if cfg.train.prediction_mode == "residual" else "softplus"

    train_loader = DataLoader(
        train_ds,
        batch_size=cfg.train.batch_size,
        shuffle=True,
        num_workers=cfg.train.num_workers,
        pin_memory=(device.type == "cuda"),
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=cfg.train.batch_size,
        shuffle=False,
        num_workers=cfg.train.num_workers,
        pin_memory=(device.type == "cuda"),
    )

    model_base = 64
    model_name = "smallunet"
    model = build_model(
        model_name=model_name,
        in_channels=in_channels,
        out_channels=out_channels,
        base=model_base,
        output_activation=output_activation,
    ).to(device)
    _load_init_checkpoint(model, init_checkpoint)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=cfg.train.learning_rate,
        weight_decay=cfg.train.weight_decay,
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=max(cfg.train.epochs, 1),
        eta_min=cfg.train.learning_rate * float(np.clip(cfg.train.cosine_eta_min_ratio, 0.0, 1.0)),
    )

    scaler = torch.amp.GradScaler("cuda", enabled=(device.type == "cuda"))

    best_val = float("inf")
    history = {"train_loss": [], "val_loss": [], "lr": []}
    best_state = None
    hard_under_w = float(getattr(cfg.train, "hard_underestimation_weight", cfg.train.underestimation_weight))
    hard_over_w = float(getattr(cfg.train, "hard_overestimation_weight", 0.0))
    narrow_over_w = float(getattr(cfg.train, "narrow_overestimation_weight", 0.0))
    hard_rank_lambda = float(getattr(cfg.train, "hard_rank_lambda", 0.0))
    hard_rank_topk = int(getattr(cfg.train, "hard_rank_topk", 64))
    hard_rank_margin = float(getattr(cfg.train, "hard_rank_margin", 0.01))
    gradient_struct_lambda = float(getattr(cfg.train, "gradient_struct_lambda", 0.0))
    laplacian_struct_lambda = float(getattr(cfg.train, "laplacian_struct_lambda", 0.0))
    local_rank_lambda = float(getattr(cfg.train, "local_rank_lambda", 0.0))
    local_rank_margin = float(getattr(cfg.train, "local_rank_margin", 0.01))
    local_rank_delta_threshold = float(getattr(cfg.train, "local_rank_delta_threshold", 0.005))
    local_rank_weight_power = float(getattr(cfg.train, "local_rank_weight_power", 1.0))
    grad_dir_lambda = float(getattr(cfg.train, "grad_dir_lambda", 0.0))
    grad_dir_min_mag = float(getattr(cfg.train, "grad_dir_min_mag", 0.01))
    local_prob_rank_lambda = float(getattr(cfg.train, "local_prob_rank_lambda", 0.0))
    local_prob_rank_tau = float(getattr(cfg.train, "local_prob_rank_tau", 0.02))
    local_prob_rank_delta_threshold = float(getattr(cfg.train, "local_prob_rank_delta_threshold", 0.003))
    local_prob_rank_focus_quantile = float(getattr(cfg.train, "local_prob_rank_focus_quantile", 0.7))
    local_prob_rank_weight_power = float(getattr(cfg.train, "local_prob_rank_weight_power", 1.0))
    local_prob_rank_hard_only = bool(getattr(cfg.train, "local_prob_rank_hard_only", True))
    local_prob_rank_narrow_boost = float(getattr(cfg.train, "local_prob_rank_narrow_boost", 0.0))
    global_rank_lambda = float(getattr(cfg.train, "global_rank_lambda", 0.0))
    global_rank_pairs = int(getattr(cfg.train, "global_rank_pairs", 96))
    global_rank_tau = float(getattr(cfg.train, "global_rank_tau", 0.04))
    global_rank_top_quantile = float(getattr(cfg.train, "global_rank_top_quantile", 0.85))
    global_rank_bottom_quantile = float(getattr(cfg.train, "global_rank_bottom_quantile", 0.25))
    global_rank_hard_only = bool(getattr(cfg.train, "global_rank_hard_only", True))
    global_rank_narrow_boost = float(getattr(cfg.train, "global_rank_narrow_boost", 0.0))
    distill_lambda = float(getattr(cfg.train, "distill_lambda", 0.0))
    distill_huber_delta = float(getattr(cfg.train, "distill_huber_delta", 0.02))
    distill_focus_quantile = float(getattr(cfg.train, "distill_focus_quantile", 0.0))
    distill_hard_only = bool(getattr(cfg.train, "distill_hard_only", False))
    distill_narrow_boost = float(getattr(cfg.train, "distill_narrow_boost", 0.0))
    distill_under_lambda = float(getattr(cfg.train, "distill_under_lambda", 0.0))

    for epoch in range(cfg.train.epochs):
        model.train()
        epoch_loss = 0.0
        n = 0

        for batch in train_loader:
            x = batch["input"].to(device, non_blocking=True)
            y = batch["target"].to(device, non_blocking=True)
            m = batch["mask"].to(device, non_blocking=True)
            lw = batch["loss_weight"].to(device, non_blocking=True)
            sw = batch.get("sample_weight")
            if sw is not None:
                sw = sw.to(device, non_blocking=True)
            hm = batch.get("is_hard")
            if hm is not None:
                hm = hm.to(device, non_blocking=True)
            sm = batch.get("is_standard")
            if sm is not None:
                sm = sm.to(device, non_blocking=True)
            nm = batch.get("narrow_mask")
            if nm is not None:
                nm = nm.to(device, non_blocking=True)
            t_steps = int(batch.get("temporal_steps", torch.tensor([1]))[0].item())
            yaw_bins = int(batch.get("yaw_bins", torch.tensor([y.shape[1]]))[0].item())

            optimizer.zero_grad(set_to_none=True)
            with torch.amp.autocast("cuda", enabled=(device.type == "cuda")):
                pred = model(x)
                loss = _masked_loss(
                    pred,
                    y,
                    m,
                    lw,
                    sw,
                    underestimation_weight=cfg.train.underestimation_weight,
                    hard_mask=hm,
                    standard_mask=sm,
                    hard_underestimation_weight=hard_under_w,
                    hard_overestimation_weight=hard_over_w,
                    narrow_mask=nm,
                    narrow_overestimation_weight=narrow_over_w,
                    temporal_steps=t_steps,
                    yaw_bins=yaw_bins,
                    temporal_lambda=0.1,
                    hard_rank_lambda=hard_rank_lambda,
                    hard_rank_topk=hard_rank_topk,
                    hard_rank_margin=hard_rank_margin,
                    gradient_struct_lambda=gradient_struct_lambda,
                    laplacian_struct_lambda=laplacian_struct_lambda,
                    local_rank_lambda=local_rank_lambda,
                    local_rank_margin=local_rank_margin,
                    local_rank_delta_threshold=local_rank_delta_threshold,
                    local_rank_weight_power=local_rank_weight_power,
                    grad_dir_lambda=grad_dir_lambda,
                    grad_dir_min_mag=grad_dir_min_mag,
                    local_prob_rank_lambda=local_prob_rank_lambda,
                    local_prob_rank_tau=local_prob_rank_tau,
                    local_prob_rank_delta_threshold=local_prob_rank_delta_threshold,
                    local_prob_rank_focus_quantile=local_prob_rank_focus_quantile,
                    local_prob_rank_weight_power=local_prob_rank_weight_power,
                    local_prob_rank_hard_only=local_prob_rank_hard_only,
                    local_prob_rank_narrow_boost=local_prob_rank_narrow_boost,
                    global_rank_lambda=global_rank_lambda,
                    global_rank_pairs=global_rank_pairs,
                    global_rank_tau=global_rank_tau,
                    global_rank_top_quantile=global_rank_top_quantile,
                    global_rank_bottom_quantile=global_rank_bottom_quantile,
                    global_rank_hard_only=global_rank_hard_only,
                    global_rank_narrow_boost=global_rank_narrow_boost,
                    distill_target=None,
                    distill_lambda=distill_lambda,
                    distill_huber_delta=distill_huber_delta,
                    distill_focus_quantile=distill_focus_quantile,
                    distill_hard_only=distill_hard_only,
                    distill_narrow_boost=distill_narrow_boost,
                    distill_under_lambda=distill_under_lambda,
                )

            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            scaler.step(optimizer)
            scaler.update()

            epoch_loss += float(loss.item())
            n += 1

        train_loss = epoch_loss / max(n, 1)
        val_loss = _eval(
            model,
            val_loader,
            device,
            underestimation_weight=cfg.train.underestimation_weight,
            hard_underestimation_weight=hard_under_w,
            hard_overestimation_weight=hard_over_w,
            narrow_overestimation_weight=narrow_over_w,
            hard_rank_lambda=hard_rank_lambda,
            hard_rank_topk=hard_rank_topk,
            hard_rank_margin=hard_rank_margin,
            gradient_struct_lambda=gradient_struct_lambda,
            laplacian_struct_lambda=laplacian_struct_lambda,
            local_rank_lambda=local_rank_lambda,
            local_rank_margin=local_rank_margin,
            local_rank_delta_threshold=local_rank_delta_threshold,
            local_rank_weight_power=local_rank_weight_power,
            grad_dir_lambda=grad_dir_lambda,
            grad_dir_min_mag=grad_dir_min_mag,
            local_prob_rank_lambda=local_prob_rank_lambda,
            local_prob_rank_tau=local_prob_rank_tau,
            local_prob_rank_delta_threshold=local_prob_rank_delta_threshold,
            local_prob_rank_focus_quantile=local_prob_rank_focus_quantile,
            local_prob_rank_weight_power=local_prob_rank_weight_power,
            local_prob_rank_hard_only=local_prob_rank_hard_only,
            local_prob_rank_narrow_boost=local_prob_rank_narrow_boost,
            global_rank_lambda=global_rank_lambda,
            global_rank_pairs=global_rank_pairs,
            global_rank_tau=global_rank_tau,
            global_rank_top_quantile=global_rank_top_quantile,
            global_rank_bottom_quantile=global_rank_bottom_quantile,
            global_rank_hard_only=global_rank_hard_only,
            global_rank_narrow_boost=global_rank_narrow_boost,
            distill_lambda=distill_lambda,
            distill_huber_delta=distill_huber_delta,
            distill_focus_quantile=distill_focus_quantile,
            distill_hard_only=distill_hard_only,
            distill_narrow_boost=distill_narrow_boost,
            distill_under_lambda=distill_under_lambda,
        )
        history["lr"].append(float(optimizer.param_groups[0]["lr"]))
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)

        print(
            f"epoch {epoch + 1:02d}/{cfg.train.epochs} "
            f"lr={optimizer.param_groups[0]['lr']:.3e} train={train_loss:.5f} val={val_loss:.5f}"
        )

        if val_loss < best_val:
            best_val = val_loss
            best_state = {k: v.detach().cpu() for k, v in model.state_dict().items()}

        scheduler.step()

    ckpt_dir = cfg.paths.checkpoints_dir
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = ckpt_dir / "heuristic_net.pt"

    payload = {
        "model_state": best_state,
        "history": history,
        "config": asdict(cfg),
        "in_channels": in_channels,
        "out_channels": out_channels,
        "base_channels": model_base,
        "prediction_mode": cfg.train.prediction_mode,
        "output_activation": output_activation,
        "residual_nonnegative": bool(cfg.train.prediction_mode == "residual"),
        "model_name": model_name,
        "temporal_steps": int(train_ds[0].get("temporal_steps", torch.tensor(1)).item()),
        "heuristic_yaw_bins": int(train_ds[0].get("yaw_bins", torch.tensor(out_channels)).item()),
    }
    torch.save(payload, ckpt_path)

    metrics = {
        "best_val_loss": float(best_val),
        "final_train_loss": float(history["train_loss"][-1]),
        "final_val_loss": float(history["val_loss"][-1]),
        "final_lr": float(history["lr"][-1]) if history["lr"] else float(cfg.train.learning_rate),
        "device": str(device),
        "in_channels": in_channels,
        "out_channels": out_channels,
        "prediction_mode": cfg.train.prediction_mode,
        "type_c_loss_weight": float(cfg.train.type_c_loss_weight),
    }

    log_path = cfg.paths.logs_dir / "train_metrics.json"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as f:
        json.dump(metrics | history, f, indent=2)

    return ckpt_path, metrics
