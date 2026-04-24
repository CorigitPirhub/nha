from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rs_macro_rescue.stack.recoverability import MacroPrimitive
from rs_macro_rescue.stack.haa_stack import FrozenHAATeacher, build_frozen_haa_teacher


@dataclass(frozen=True)
class MacroRescueSliceSpec:
    bridge_min: float
    bridge_max: float
    focus_min: float
    focus_max: float
    path_min: float
    path_max: float


def build_frozen_haa_stack(train_assets, val_assets, predictor, cfg, device: str, out_dir: Path, dependencies: dict[str, Any] | None = None) -> FrozenHAATeacher:
    if isinstance(dependencies, dict) and isinstance(dependencies.get('haa_teacher'), FrozenHAATeacher):
        return dependencies['haa_teacher']
    return build_frozen_haa_teacher(train_assets, val_assets, predictor, cfg, device, out_dir, dependencies)


def scene_values(bundle: dict[str, Any]) -> tuple[float, float, float]:
    scene = dict(bundle.get('scene', {}))
    return (
        float(scene.get('bridge_diffuse', 0.0)),
        float(scene.get('focus_gap', 0.0)),
        float(scene.get('path_openness', 0.0)),
    )


def scene_match(bundle: dict[str, Any], spec: MacroRescueSliceSpec) -> bool:
    bridge, focus, path_open = scene_values(bundle)
    return bool(
        float(spec.bridge_min) <= bridge <= float(spec.bridge_max)
        and float(spec.focus_min) <= focus <= float(spec.focus_max)
        and float(spec.path_min) <= path_open <= float(spec.path_max)
    )


CUSTOM_MACRO_REV2 = MacroPrimitive(
    name='macro_misc_rev2',
    primitive_indices=(9, 9),
    family='macro:reverse',
    avg_gain=0.0,
    hits=0,
)


__all__ = [
    'CUSTOM_MACRO_REV2',
    'MacroRescueSliceSpec',
    'build_frozen_haa_stack',
    'scene_match',
    'scene_values',
]
