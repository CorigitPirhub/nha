from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
from utils.common import yaw_to_bin_float


def save_field_overview(
    occupancy: np.ndarray,
    esdf: np.ndarray,
    teacher: np.ndarray,
    pred: Optional[np.ndarray],
    out_path: Path,
    title: str = "field_overview",
) -> None:
    n_cols = 4 if pred is not None else 3
    fig, axes = plt.subplots(1, n_cols, figsize=(4 * n_cols, 4), constrained_layout=True)

    ax = axes[0]
    ax.imshow(occupancy, cmap="gray_r", origin="lower")
    ax.set_title("Occupancy")
    ax.set_axis_off()

    ax = axes[1]
    im1 = ax.imshow(esdf, cmap="coolwarm", origin="lower")
    ax.set_title("ESDF")
    ax.set_axis_off()
    fig.colorbar(im1, ax=ax, fraction=0.046)

    ax = axes[2]
    im2 = ax.imshow(teacher, cmap="viridis", origin="lower")
    ax.set_title("Teacher Heuristic")
    ax.set_axis_off()
    fig.colorbar(im2, ax=ax, fraction=0.046)

    if pred is not None:
        ax = axes[3]
        im3 = ax.imshow(pred, cmap="viridis", origin="lower")
        ax.set_title("Predicted Heuristic")
        ax.set_axis_off()
        fig.colorbar(im3, ax=ax, fraction=0.046)

    fig.suptitle(title)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def save_path_comparison(
    occupancy: np.ndarray,
    baseline_path: np.ndarray,
    neural_path: np.ndarray,
    resolution: float,
    out_path: Path,
    start: tuple[float, float, float],
    goal: tuple[float, float, float],
    title: str = "path_compare",
) -> None:
    fig, ax = plt.subplots(1, 1, figsize=(6, 6), constrained_layout=True)
    ax.imshow(occupancy, cmap="gray_r", origin="lower")

    if baseline_path.size > 0:
        bx = baseline_path[:, 0] / resolution - 0.5
        by = baseline_path[:, 1] / resolution - 0.5
        ax.plot(bx, by, color="tab:blue", linewidth=2.0, label="baseline")

    if neural_path.size > 0:
        nx = neural_path[:, 0] / resolution - 0.5
        ny = neural_path[:, 1] / resolution - 0.5
        ax.plot(nx, ny, color="tab:orange", linewidth=2.0, label="neural-guided")

    sx = start[0] / resolution - 0.5
    sy = start[1] / resolution - 0.5
    gx = goal[0] / resolution - 0.5
    gy = goal[1] / resolution - 0.5

    ax.scatter([sx], [sy], c="lime", s=70, edgecolors="black", label="start")
    ax.scatter([gx], [gy], c="red", s=70, edgecolors="black", label="goal")

    ax.legend(loc="upper right")
    ax.set_title(title)
    ax.set_axis_off()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def save_training_curve(train_loss: list[float], val_loss: list[float], out_path: Path) -> None:
    fig, ax = plt.subplots(1, 1, figsize=(6, 4), constrained_layout=True)
    ax.plot(train_loss, label="train")
    ax.plot(val_loss, label="val")
    ax.set_xlabel("epoch")
    ax.set_ylabel("loss")
    ax.set_title("Training Curve")
    ax.grid(True, alpha=0.3)
    ax.legend()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def save_search_tree_comparison(
    occupancy: np.ndarray,
    euclidean_expanded: np.ndarray,
    ours_expanded: np.ndarray,
    euclidean_path: np.ndarray,
    ours_path: np.ndarray,
    resolution: float,
    start: tuple[float, float, float],
    goal: tuple[float, float, float],
    out_path: Path,
    title: str = "search_tree_compare",
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), constrained_layout=True)
    panels = [
        (axes[0], euclidean_expanded, euclidean_path, "Euclidean"),
        (axes[1], ours_expanded, ours_path, "Ours (Neural Guided)"),
    ]
    for ax, expanded, path, name in panels:
        ax.imshow(occupancy, cmap="gray_r", origin="lower")
        if expanded.size > 0:
            ex = expanded[:, 0] / resolution - 0.5
            ey = expanded[:, 1] / resolution - 0.5
            ax.scatter(ex, ey, s=1.0, c="deepskyblue", alpha=0.35, linewidths=0)
        if path.size > 0:
            px = path[:, 0] / resolution - 0.5
            py = path[:, 1] / resolution - 0.5
            ax.plot(px, py, color="orange", linewidth=2.0)
        sx = start[0] / resolution - 0.5
        sy = start[1] / resolution - 0.5
        gx = goal[0] / resolution - 0.5
        gy = goal[1] / resolution - 0.5
        ax.scatter([sx], [sy], c="lime", s=70, edgecolors="black")
        ax.scatter([gx], [gy], c="red", s=70, edgecolors="black")
        ax.set_title(name)
        ax.set_axis_off()
    fig.suptitle(title)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def save_nonholonomic_field_comparison(
    occupancy: np.ndarray,
    teacher_3d: np.ndarray,
    pred_3d: np.ndarray,
    goal: tuple[float, float, float],
    yaw_ref: float,
    resolution: float,
    out_path: Path,
    title: str = "nonholonomic_field_compare",
) -> None:
    if teacher_3d is None or pred_3d is None:
        return
    if teacher_3d.ndim != 3 or pred_3d.ndim != 3:
        return

    k_t = int(np.floor(yaw_to_bin_float(yaw_ref, teacher_3d.shape[0]))) % teacher_3d.shape[0]
    k_p = int(np.floor(yaw_to_bin_float(yaw_ref, pred_3d.shape[0]))) % pred_3d.shape[0]

    teacher_slice = teacher_3d[k_t]
    pred_slice = pred_3d[k_p]

    h, w = occupancy.shape
    yy, xx = np.mgrid[0:h, 0:w]
    wx = (xx + 0.5) * resolution
    wy = (yy + 0.5) * resolution
    euc = np.hypot(wx - goal[0], wy - goal[1]).astype(np.float32)

    vmax = np.percentile(teacher_slice[~occupancy], 96) if np.any(~occupancy) else np.max(teacher_slice)
    vmax = max(1.0, float(vmax))

    fig, axes = plt.subplots(1, 3, figsize=(12, 4), constrained_layout=True)
    for ax, mat, name in [
        (axes[0], teacher_slice, "Teacher (yaw-slice)"),
        (axes[1], pred_slice, "Prediction (yaw-slice)"),
        (axes[2], euc, "Euclidean"),
    ]:
        im = ax.imshow(mat, cmap="viridis", origin="lower", vmin=0.0, vmax=vmax)
        ax.contour(occupancy.astype(float), levels=[0.5], colors="white", linewidths=0.6)
        ax.set_title(name)
        ax.set_axis_off()
        fig.colorbar(im, ax=ax, fraction=0.046)
    fig.suptitle(title)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=170)
    plt.close(fig)
