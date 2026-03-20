# P0-CX34-A Hard Eval V1

- protocol: frozen hard-test evaluation; no retuning after public acceptance
- canonical chosen json: `outputs/rs_p0cx34_a_pilot_v1/chosen.json`
- parent chosen json: `outputs/rs_p0cx33_b_pilot_v1/chosen.json`
- hard root: `data/benchmark/rs_root_hard_v2/test`
- fixed cap: `20000`
- device: `cuda`
- frozen mainline params: `{'turn_bridge_max': 0.1, 'turn_focus_max': 0.36, 'rescue_bridge_max': 0.08, 'rescue_focus_min': 0.39, 'rescue_path_min': 0.99, 'rescue_budget': 1, 'suppress_bridge_min': 0.11, 'suppress_bridge_max': 0.13, 'suppress_focus_max': 0.31, 'suppress_path_min': 0.97, 'stubborn_bridge_min': 0.125, 'stubborn_focus_max': 0.34, 'stubborn_path_max': 0.97, 'macro_bridge_min': 0.078, 'macro_bridge_max': 0.095, 'macro_focus_min': 0.34, 'macro_focus_max': 0.37, 'macro_path_min': 0.97, 'macro_path_max': 1.01, 'maze_revisit_thr': 2, 'maze_stall_steps': 18, 'reverse_required_thr': 0.1, 'trap_thr': 0.54, 'progress_eps': 0.02, 'commit_fail_margin': 0.05, 'failure_ttl': 32, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24}`
- frozen parent params: `{'maze_revisit_thr': 2, 'maze_stall_steps': 18, 'reverse_required_thr': 0.1, 'trap_thr': 0.54, 'turn_bridge_max': 0.1, 'turn_focus_max': 0.36, 'rescue_bridge_max': 0.08, 'rescue_focus_min': 0.39, 'rescue_path_min': 0.99, 'rescue_target': 'escape_border|reverse', 'rescue_budget': 1, 'suppress_bridge_min': 0.11, 'suppress_bridge_max': 0.13, 'suppress_focus_max': 0.31, 'suppress_path_min': 0.97, 'suppress_target': 'uncertain|none', 'stubborn_bridge_min': 0.125, 'stubborn_focus_max': 0.34, 'stubborn_path_max': 0.97, 'stubborn_target': 'forward_safe|forward_turn', 'progress_eps': 0.02, 'commit_fail_margin': 0.05, 'failure_ttl': 32, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24}`
- inputs sha256: `outputs/rs_p0cx34_a_hard_eval_cuda_v1/inputs_sha256.json`

## Hard Benchmark vs `CX3-D`
- `CX34-A (Mainline)`: success_delta_pp=`2.740`, exp_delta=`196.548`, mean_time_overhead_ratio=`2.592819`, path_delta=`-1.179`

## Hard Family Breakdown vs `CX3-D`
- `alpha_puzzle` / `CX34-A (Mainline)`: success_delta_pp=`9.091`, exp_delta=`87.364`, mean_time_overhead_ratio=`2.645572`, path_delta=`-20.510`
- `bug_trap` / `CX34-A (Mainline)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`2.727361`, path_delta=`0.000`
- `deadend_labyrinth` / `CX34-A (Mainline)`: success_delta_pp=`0.000`, exp_delta=`-361.100`, mean_time_overhead_ratio=`2.892117`, path_delta=`0.452`
- `flange` / `CX34-A (Mainline)`: success_delta_pp=`0.000`, exp_delta=`-41.538`, mean_time_overhead_ratio=`2.685927`, path_delta=`-0.230`
- `maze` / `CX34-A (Mainline)`: success_delta_pp=`9.091`, exp_delta=`1274.455`, mean_time_overhead_ratio=`2.277483`, path_delta=`-0.499`
- `narrow_passage` / `CX34-A (Mainline)`: success_delta_pp=`0.000`, exp_delta=`273.615`, mean_time_overhead_ratio=`2.387442`, path_delta=`-0.038`
- `parasol_misc` / `CX34-A (Mainline)`: success_delta_pp=`0.000`, exp_delta=`-9.500`, mean_time_overhead_ratio=`3.429126`, path_delta=`-0.056`

## Verdict
- overall hard-test gate is positive: `CX34-A` improves both success and expansions relative to `CX3-D`
- the strongest hard-test leverage comes from `maze`, `narrow_passage`, and the `alpha_puzzle` success lift
- the remaining hard-test liabilities are concentrated in `deadend_labyrinth`, `flange`, and `parasol_misc`
- this hard-test eval upgrades `CX34-A` from a public-only branch to a branch with frozen hard-test support, but it does **not** resolve deployable runtime or path-quality caveats
