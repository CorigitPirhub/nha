from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib.animation as animation
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


def save_efficiency_scatter(summary: dict, out_path: Path, title: str = "Efficiency-Quality Tradeoff") -> None:
    methods = ["euclidean", "dubins", "rs_consistent", "ours"]
    labels = {
        "euclidean": "Euclidean",
        "dubins": "Dubins",
        "rs_consistent": "RS-Analytical",
        "ours": "Ours",
    }
    colors = {
        "euclidean": "#1f77b4",
        "dubins": "#ff7f0e",
        "rs_consistent": "#2ca02c",
        "ours": "#d62728",
    }
    m = summary.get("methods", {})
    fig, ax = plt.subplots(1, 1, figsize=(6.5, 5), constrained_layout=True)
    for k in methods:
        if k not in m:
            continue
        v = m[k]
        x = float(v.get("avg_time_total_ms", v.get("avg_time_ms", np.nan)))
        y = float(v.get("avg_expansions", np.nan))
        if not np.isfinite(x) or not np.isfinite(y):
            continue
        ax.scatter([x], [y], s=85, color=colors[k], label=labels[k], edgecolors="black", linewidths=0.6)
        ax.annotate(labels[k], (x, y), textcoords="offset points", xytext=(6, 6), fontsize=9)
    ax.set_xlabel("Total Runtime (ms)")
    ax.set_ylabel("Average Expanded Nodes")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def _to_grid_xy(points: np.ndarray, resolution: float, max_points: int) -> np.ndarray:
    if points is None:
        return np.zeros((0, 2), dtype=np.float32)
    arr = np.asarray(points, dtype=np.float32)
    if arr.ndim != 2 or arr.shape[1] < 2:
        return np.zeros((0, 2), dtype=np.float32)
    xy = arr[:, :2]
    if xy.shape[0] > max_points:
        idx = np.linspace(0, xy.shape[0] - 1, max_points, dtype=np.int32)
        xy = xy[idx]
    gx = xy[:, 0] / float(resolution) - 0.5
    gy = xy[:, 1] / float(resolution) - 0.5
    return np.stack([gx, gy], axis=1).astype(np.float32)


def _try_save_animation(anim: animation.FuncAnimation, out_path: Path, fps: int, dpi: int) -> Path:
    out_path = Path(out_path)
    ext = out_path.suffix.lower()
    if ext not in {".mp4", ".gif"}:
        out_path = out_path.with_suffix(".mp4")
        ext = ".mp4"
    has_ffmpeg = animation.writers.is_available("ffmpeg")
    has_pillow = animation.writers.is_available("pillow")

    if ext == ".gif":
        if not has_pillow:
            raise RuntimeError("GIF export requires matplotlib pillow writer. Please install pillow.")
        anim.save(out_path, writer="pillow", fps=fps, dpi=dpi)
        return out_path

    if has_ffmpeg:
        try:
            anim.save(out_path, writer="ffmpeg", fps=fps, dpi=dpi, bitrate=1800)
            return out_path
        except Exception:
            pass

    if not has_pillow:
        raise RuntimeError(
            "MP4 export failed and GIF fallback is unavailable (pillow writer missing). "
            "Install ffmpeg or pillow."
        )
    fallback = out_path.with_suffix(".gif")
    anim.save(fallback, writer="pillow", fps=min(max(fps, 1), 20), dpi=dpi)
    return fallback


def save_search_progress_animation(
    occupancy: np.ndarray,
    euclidean_expanded: np.ndarray,
    ours_expanded: np.ndarray,
    euclidean_path: np.ndarray,
    ours_path: np.ndarray,
    resolution: float,
    start: tuple[float, float, float],
    goal: tuple[float, float, float],
    out_path: Path,
    title: str = "Planning Process Animation",
    fps: int = 20,
    max_frames: int = 220,
    max_expand_points: int = 4500,
) -> Path:
    eu_exp_xy = _to_grid_xy(euclidean_expanded, resolution, max_expand_points)
    ou_exp_xy = _to_grid_xy(ours_expanded, resolution, max_expand_points)
    eu_path_xy = _to_grid_xy(euclidean_path, resolution, max_expand_points)
    ou_path_xy = _to_grid_xy(ours_path, resolution, max_expand_points)

    sx = start[0] / resolution - 0.5
    sy = start[1] / resolution - 0.5
    gx = goal[0] / resolution - 0.5
    gy = goal[1] / resolution - 0.5

    n_expand_frames = max(20, int(max_frames * 0.72))
    n_path_frames = max(12, int(max_frames * 0.20))
    n_hold_frames = max(8, max_frames - n_expand_frames - n_path_frames)
    total_frames = n_expand_frames + n_path_frames + n_hold_frames

    eu_expand_progress = np.linspace(0, eu_exp_xy.shape[0], n_expand_frames, dtype=np.int32)
    ou_expand_progress = np.linspace(0, ou_exp_xy.shape[0], n_expand_frames, dtype=np.int32)
    eu_path_progress = np.linspace(0, eu_path_xy.shape[0], n_path_frames, dtype=np.int32)
    ou_path_progress = np.linspace(0, ou_path_xy.shape[0], n_path_frames, dtype=np.int32)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), constrained_layout=True)
    styles = [
        (axes[0], "Euclidean", eu_exp_xy, eu_path_xy),
        (axes[1], "Ours (RS + Residual)", ou_exp_xy, ou_path_xy),
    ]
    scatters = []
    lines = []
    for ax, name, _, _ in styles:
        ax.imshow(occupancy, cmap="gray_r", origin="lower")
        sc = ax.scatter([], [], s=1.5, c="deepskyblue", alpha=0.45, linewidths=0)
        ln, = ax.plot([], [], color="orange", linewidth=2.2)
        ax.scatter([sx], [sy], c="lime", s=60, edgecolors="black", zorder=5)
        ax.scatter([gx], [gy], c="red", s=60, edgecolors="black", zorder=5)
        ax.set_title(name)
        ax.set_axis_off()
        scatters.append(sc)
        lines.append(ln)

    def _set_offsets(scatter_obj, pts: np.ndarray) -> None:
        if pts.shape[0] == 0:
            scatter_obj.set_offsets(np.zeros((0, 2), dtype=np.float32))
            return
        scatter_obj.set_offsets(pts)

    def _set_line(line_obj, pts: np.ndarray) -> None:
        if pts.shape[0] == 0:
            line_obj.set_data([], [])
            return
        line_obj.set_data(pts[:, 0], pts[:, 1])

    def _update(frame_idx: int):
        if frame_idx < n_expand_frames:
            e_n = int(eu_expand_progress[frame_idx])
            o_n = int(ou_expand_progress[frame_idx])
            _set_offsets(scatters[0], eu_exp_xy[:e_n])
            _set_offsets(scatters[1], ou_exp_xy[:o_n])
            _set_line(lines[0], np.zeros((0, 2), dtype=np.float32))
            _set_line(lines[1], np.zeros((0, 2), dtype=np.float32))
            pct = int((frame_idx + 1) * 100 / max(n_expand_frames, 1))
            fig.suptitle(f"{title} | Search Expansion {pct}%")
        elif frame_idx < n_expand_frames + n_path_frames:
            p_idx = frame_idx - n_expand_frames
            e_n = int(eu_path_progress[p_idx])
            o_n = int(ou_path_progress[p_idx])
            _set_offsets(scatters[0], eu_exp_xy)
            _set_offsets(scatters[1], ou_exp_xy)
            _set_line(lines[0], eu_path_xy[:e_n])
            _set_line(lines[1], ou_path_xy[:o_n])
            pct = int((p_idx + 1) * 100 / max(n_path_frames, 1))
            fig.suptitle(f"{title} | Path Reconstruction {pct}%")
        else:
            _set_offsets(scatters[0], eu_exp_xy)
            _set_offsets(scatters[1], ou_exp_xy)
            _set_line(lines[0], eu_path_xy)
            _set_line(lines[1], ou_path_xy)
            fig.suptitle(f"{title} | Completed")
        return [*scatters, *lines]

    anim = animation.FuncAnimation(
        fig,
        _update,
        frames=total_frames,
        interval=1000.0 / max(int(fps), 1),
        blit=False,
        repeat=False,
    )
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        return _try_save_animation(anim, out_path=out_path, fps=max(int(fps), 1), dpi=150)
    finally:
        plt.close(fig)
