from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np


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
