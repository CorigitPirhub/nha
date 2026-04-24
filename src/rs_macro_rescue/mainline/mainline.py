from __future__ import annotations

from pathlib import Path

from rs_macro_rescue.mainline.macro_rescue import MacroRescueParams


CURRENT_RS_MAINLINE_NAME = 'RS + Macro Rescue / Subtype-Specific Macro Rescue'
CURRENT_RS_MAINLINE_SCOPE = 'external datasets only: csm, mp, parasol_narrow'
CURRENT_RS_MAINLINE_CANONICAL_DEVICE = 'cpu'

DEFAULT_EXTERNAL_EVAL_OUTPUT_ROOT = Path('outputs/rs_macro_rescue_external_eval')
DEFAULT_EXTERNAL_EVAL_REPORT = Path('reports/rs_macro_rescue_external_eval.md')

CURRENT_RS_MAINLINE_PARAMS = MacroRescueParams(
    turn_bridge_max=0.10,
    turn_focus_max=0.36,
    rescue_bridge_max=0.08,
    rescue_focus_min=0.39,
    rescue_path_min=0.99,
    rescue_budget=1,
    suppress_bridge_min=0.11,
    suppress_bridge_max=0.13,
    suppress_focus_max=0.31,
    suppress_path_min=0.97,
    stubborn_bridge_min=0.125,
    stubborn_focus_max=0.34,
    stubborn_path_max=0.97,
    macro_bridge_min=0.078,
    macro_bridge_max=0.095,
    macro_focus_min=0.34,
    macro_focus_max=0.37,
    macro_path_min=0.97,
    macro_path_max=1.01,
    maze_revisit_thr=2,
    maze_stall_steps=18,
    reverse_required_thr=0.10,
    trap_thr=0.54,
    progress_eps=0.02,
    commit_fail_margin=0.05,
    failure_ttl=32,
    history_window=16,
    cell_stride=2,
    yaw_bins=24,
)


def load_current_mainline_params() -> MacroRescueParams:
    return CURRENT_RS_MAINLINE_PARAMS


__all__ = [
    'CURRENT_RS_MAINLINE_CANONICAL_DEVICE',
    'CURRENT_RS_MAINLINE_NAME',
    'CURRENT_RS_MAINLINE_PARAMS',
    'CURRENT_RS_MAINLINE_SCOPE',
    'DEFAULT_EXTERNAL_EVAL_OUTPUT_ROOT',
    'DEFAULT_EXTERNAL_EVAL_REPORT',
    'load_current_mainline_params',
]
