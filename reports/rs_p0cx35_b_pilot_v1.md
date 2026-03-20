# CX35-B Pilot V1

- protocol: frozen `CX34-A / Subtype-Specific Macro Rescue` parent on public evidence; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit
- research anchors:
  - Experience Graphs / reusable planning structure: Phillips et al., ICRA 2012 — https://www.ri.cmu.edu/pub_files/2012/5/icra12.pdf
  - Model preconditions / structural option applicability: Ravichandar et al., CoRL 2021 — https://proceedings.mlr.press/v164/ravichandar22a.html
  - Motion primitives in state lattices: Pivtoraiko & Kelly, iSAIRAS 2005
  - Motion planning with maneuver automata: Schouwenaars et al., ACC 2001 / hybrid systems maneuver automation line
- chosen params: `{'turn_bridge_max': 0.1, 'turn_focus_max': 0.36, 'rescue_bridge_max': 0.08, 'rescue_focus_min': 0.39, 'rescue_path_min': 0.99, 'rescue_budget': 1, 'suppress_bridge_min': 0.11, 'suppress_bridge_max': 0.13, 'suppress_focus_max': 0.31, 'suppress_path_min': 0.97, 'stubborn_bridge_min': 0.125, 'stubborn_focus_max': 0.34, 'stubborn_path_max': 0.97, 'macro_bridge_min': 0.078, 'macro_bridge_max': 0.095, 'macro_focus_min': 0.34, 'macro_focus_max': 0.37, 'macro_path_min': 0.97, 'macro_path_max': 1.01, 'maze_revisit_thr': 2, 'maze_stall_steps': 18, 'reverse_required_thr': 0.1, 'trap_thr': 0.54, 'progress_eps': 0.02, 'commit_fail_margin': 0.05, 'failure_ttl': 32, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24, 'min_hits': 2}`
- output root: `outputs/rs_p0cx35_rerun_v2/rs_p0cx35_b_pilot_v1`

## Public vs `CX3-D`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`420.389`, mean_time_overhead_ratio=`3.527234`
- `CX35-B (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.458320`
- `CX35-B (No-Typed-Family-Choice)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.459173`

## Public Family Breakdown vs `CX3-D`
- `alpha_puzzle` / `CX34-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.323819`
- `alpha_puzzle` / `CX35-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.970550`
- `alpha_puzzle` / `CX35-B (No-Typed-Family-Choice)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.939485`
- `bug_trap` / `CX34-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.307586`
- `bug_trap` / `CX35-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.850802`
- `bug_trap` / `CX35-B (No-Typed-Family-Choice)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.845430`
- `flange` / `CX34-A (Full)`: exp_delta=`1421.000`, mean_time_overhead_ratio=`3.336465`
- `flange` / `CX35-B (Full)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.303635`
- `flange` / `CX35-B (No-Typed-Family-Choice)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.312812`
- `maze` / `CX34-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`3.914200`
- `maze` / `CX35-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.780985`
- `maze` / `CX35-B (No-Typed-Family-Choice)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.769023`
- `narrow_passage` / `CX34-A (Full)`: exp_delta=`99.750`, mean_time_overhead_ratio=`3.789361`
- `narrow_passage` / `CX35-B (Full)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.651495`
- `narrow_passage` / `CX35-B (No-Typed-Family-Choice)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.664766`
- `parasol_misc` / `CX34-A (Full)`: exp_delta=`10.500`, mean_time_overhead_ratio=`4.660825`
- `parasol_misc` / `CX35-B (Full)`: exp_delta=`12.333`, mean_time_overhead_ratio=`3.560978`
- `parasol_misc` / `CX35-B (No-Typed-Family-Choice)`: exp_delta=`12.333`, mean_time_overhead_ratio=`3.287134`

## Public vs `CX34-A (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-420.389`, mean_time_overhead_ratio=`-0.779115`
- `CX35-B (Full)`: success_delta_pp=`0.000`, exp_delta=`2.333`, mean_time_overhead_ratio=`-0.236108`
- `CX35-B (No-Typed-Family-Choice)`: success_delta_pp=`0.000`, exp_delta=`2.333`, mean_time_overhead_ratio=`-0.235919`

## Public Family Breakdown vs `CX34-A (Full)`
- `alpha_puzzle` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.812165`
- `alpha_puzzle` / `CX35-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.254191`
- `alpha_puzzle` / `CX35-B (No-Typed-Family-Choice)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.260026`
- `bug_trap` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.811590`
- `bug_trap` / `CX35-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.274472`
- `bug_trap` / `CX35-B (No-Typed-Family-Choice)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.275484`
- `flange` / `CX3-D`: exp_delta=`-1421.000`, mean_time_overhead_ratio=`-0.769397`
- `flange` / `CX35-B (Full)`: exp_delta=`7.400`, mean_time_overhead_ratio=`-0.238173`
- `flange` / `CX35-B (No-Typed-Family-Choice)`: exp_delta=`7.400`, mean_time_overhead_ratio=`-0.236057`
- `maze` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.796508`
- `maze` / `CX35-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.230600`
- `maze` / `CX35-B (No-Typed-Family-Choice)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.233034`
- `narrow_passage` / `CX3-D`: exp_delta=`-99.750`, mean_time_overhead_ratio=`-0.791204`
- `narrow_passage` / `CX35-B (Full)`: exp_delta=`-1.500`, mean_time_overhead_ratio=`-0.237582`
- `narrow_passage` / `CX35-B (No-Typed-Family-Choice)`: exp_delta=`-1.500`, mean_time_overhead_ratio=`-0.234811`
- `parasol_misc` / `CX3-D`: exp_delta=`-10.500`, mean_time_overhead_ratio=`-0.823347`
- `parasol_misc` / `CX35-B (Full)`: exp_delta=`1.833`, mean_time_overhead_ratio=`-0.194291`
- `parasol_misc` / `CX35-B (No-Typed-Family-Choice)`: exp_delta=`1.833`, mean_time_overhead_ratio=`-0.242666`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`