from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Tuple


@dataclass
class VehicleConfig:
    wheel_base: float = 2.7
    length: float = 4.5
    width: float = 2.0
    max_steer_deg: float = 35.0
    min_turn_radius: float = 4.0


@dataclass
class MapConfig:
    width: int = 64
    height: int = 64
    resolution: float = 0.5
    obstacle_density_range: Tuple[float, float] = (0.04, 0.14)


@dataclass
class PlannerConfig:
    step_size: float = 0.6
    collision_check_step: float = 0.15
    yaw_bins: int = 72
    goal_tolerance_xy: float = 1.0
    goal_tolerance_yaw_deg: float = 40.0
    max_expansions: int = 120000
    reverse_penalty: float = 1.2
    steer_penalty: float = 0.05
    steer_change_penalty: float = 0.05
    residual_alpha: float = 1.1
    guidance_blend: float = 0.70
    warm_start_budget: int = 0


@dataclass
class DatasetConfig:
    train_size: int = 120
    val_size: int = 24
    test_size: int = 20
    gaussian_sigma: float = 2.5
    min_start_goal_dist_m: float = 8.0
    max_teacher_value: float = 1e6
    teacher_yaw_bins: int = 24
    teacher_mode: str = "hybrid_rs_consistent_esdf"
    teacher_rs_backend: str = "auto"
    teacher_rs_step_size: float = 1.0
    hybrid_obstacle_alpha: float = 0.0
    hybrid_obstacle_threshold_m: float = 1.5
    benchmark_train_counts: Tuple[int, int, int] = (40, 40, 40)  # A, B, C
    benchmark_val_counts: Tuple[int, int, int] = (8, 8, 8)
    benchmark_test_counts: Tuple[int, int, int] = (12, 12, 12)


@dataclass
class TrainConfig:
    batch_size: int = 8
    epochs: int = 20
    learning_rate: float = 1e-3
    weight_decay: float = 1e-5
    num_workers: int = 0
    device: str = "cuda"
    cosine_eta_min_ratio: float = 0.1
    underestimation_weight: float = 2.0
    distance_weight_scale_m: float = 6.0
    distance_weight_min: float = 0.25
    type_c_loss_weight: float = 1.0
    prediction_mode: str = "absolute"  # "absolute" | "residual"


@dataclass
class Paths:
    root: Path = Path(".")
    data_dir: Path = Path("data")
    output_dir: Path = Path("outputs")
    checkpoints_dir: Path = Path("outputs/checkpoints")
    figures_dir: Path = Path("outputs/figures")
    logs_dir: Path = Path("outputs/logs")


@dataclass
class ExperimentConfig:
    seed: int = 7
    vehicle: VehicleConfig = field(default_factory=VehicleConfig)
    map: MapConfig = field(default_factory=MapConfig)
    planner: PlannerConfig = field(default_factory=PlannerConfig)
    dataset: DatasetConfig = field(default_factory=DatasetConfig)
    train: TrainConfig = field(default_factory=TrainConfig)
    paths: Paths = field(default_factory=Paths)


DEFAULT_CONFIG = ExperimentConfig()
