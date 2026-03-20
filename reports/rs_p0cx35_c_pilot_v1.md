# CX35-C Pilot V1

- protocol: frozen `CX34-A / Subtype-Specific Macro Rescue` parent on public evidence; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit
- research anchors:
  - Experience Graphs / reusable planning structure: Phillips et al., ICRA 2012 — https://www.ri.cmu.edu/pub_files/2012/5/icra12.pdf
  - Model preconditions / structural option applicability: Ravichandar et al., CoRL 2021 — https://proceedings.mlr.press/v164/ravichandar22a.html
  - Motion primitives in state lattices: Pivtoraiko & Kelly, iSAIRAS 2005
  - Motion planning with maneuver automata: Schouwenaars et al., ACC 2001 / hybrid systems maneuver automation line
- chosen params: `{'turn_bridge_max': 0.1, 'turn_focus_max': 0.36, 'rescue_bridge_max': 0.08, 'rescue_focus_min': 0.39, 'rescue_path_min': 0.99, 'rescue_budget': 1, 'suppress_bridge_min': 0.11, 'suppress_bridge_max': 0.13, 'suppress_focus_max': 0.31, 'suppress_path_min': 0.97, 'stubborn_bridge_min': 0.125, 'stubborn_focus_max': 0.34, 'stubborn_path_max': 0.97, 'macro_bridge_min': 0.078, 'macro_bridge_max': 0.095, 'macro_focus_min': 0.34, 'macro_focus_max': 0.37, 'macro_path_min': 0.97, 'macro_path_max': 1.01, 'maze_revisit_thr': 2, 'maze_stall_steps': 18, 'reverse_required_thr': 0.1, 'trap_thr': 0.54, 'progress_eps': 0.02, 'commit_fail_margin': 0.05, 'failure_ttl': 32, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24, 'min_hits': 2}`
- output root: `outputs/rs_p0cx35_rerun_v3/rs_p0cx35_c_pilot_v1`

## Public vs `CX3-D`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`420.389`, mean_time_overhead_ratio=`3.527234`
- `CX35-C (Full)`: success_delta_pp=`0.000`, exp_delta=`355.222`, mean_time_overhead_ratio=`3.481344`
- `CX35-C (No-Typed-Family-Choice)`: success_delta_pp=`0.000`, exp_delta=`355.222`, mean_time_overhead_ratio=`3.473610`
- `CX35-C (No-Witness-Expansion)`: success_delta_pp=`0.000`, exp_delta=`412.722`, mean_time_overhead_ratio=`3.421067`

## Public Family Breakdown vs `CX3-D`
- `alpha_puzzle` / `CX34-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.323819`
- `alpha_puzzle` / `CX35-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`3.152348`
- `alpha_puzzle` / `CX35-C (No-Typed-Family-Choice)`: exp_delta=`0.000`, mean_time_overhead_ratio=`3.191074`
- `alpha_puzzle` / `CX35-C (No-Witness-Expansion)`: exp_delta=`0.000`, mean_time_overhead_ratio=`3.228216`
- `bug_trap` / `CX34-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.307586`
- `bug_trap` / `CX35-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`3.330355`
- `bug_trap` / `CX35-C (No-Typed-Family-Choice)`: exp_delta=`0.000`, mean_time_overhead_ratio=`3.392871`
- `bug_trap` / `CX35-C (No-Witness-Expansion)`: exp_delta=`0.000`, mean_time_overhead_ratio=`3.457319`
- `flange` / `CX34-A (Full)`: exp_delta=`1421.000`, mean_time_overhead_ratio=`3.336465`
- `flange` / `CX35-C (Full)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`3.127482`
- `flange` / `CX35-C (No-Typed-Family-Choice)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`3.122930`
- `flange` / `CX35-C (No-Witness-Expansion)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`3.130964`
- `maze` / `CX34-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`3.914200`
- `maze` / `CX35-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.397183`
- `maze` / `CX35-C (No-Typed-Family-Choice)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.334530`
- `maze` / `CX35-C (No-Witness-Expansion)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.332013`
- `narrow_passage` / `CX34-A (Full)`: exp_delta=`99.750`, mean_time_overhead_ratio=`3.789361`
- `narrow_passage` / `CX35-C (Full)`: exp_delta=`-160.500`, mean_time_overhead_ratio=`4.137260`
- `narrow_passage` / `CX35-C (No-Typed-Family-Choice)`: exp_delta=`-160.500`, mean_time_overhead_ratio=`4.125005`
- `narrow_passage` / `CX35-C (No-Witness-Expansion)`: exp_delta=`98.250`, mean_time_overhead_ratio=`3.945108`
- `parasol_misc` / `CX34-A (Full)`: exp_delta=`10.500`, mean_time_overhead_ratio=`4.660825`
- `parasol_misc` / `CX35-C (Full)`: exp_delta=`-17.667`, mean_time_overhead_ratio=`3.987794`
- `parasol_misc` / `CX35-C (No-Typed-Family-Choice)`: exp_delta=`-17.667`, mean_time_overhead_ratio=`3.964477`
- `parasol_misc` / `CX35-C (No-Witness-Expansion)`: exp_delta=`-17.667`, mean_time_overhead_ratio=`3.956443`

## Public vs `CX34-A (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-420.389`, mean_time_overhead_ratio=`-0.779115`
- `CX35-C (Full)`: success_delta_pp=`0.000`, exp_delta=`-65.167`, mean_time_overhead_ratio=`-0.010136`
- `CX35-C (No-Typed-Family-Choice)`: success_delta_pp=`0.000`, exp_delta=`-65.167`, mean_time_overhead_ratio=`-0.011845`
- `CX35-C (No-Witness-Expansion)`: success_delta_pp=`0.000`, exp_delta=`-7.667`, mean_time_overhead_ratio=`-0.023451`

## Public Family Breakdown vs `CX34-A (Full)`
- `alpha_puzzle` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.812165`
- `alpha_puzzle` / `CX35-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.220043`
- `alpha_puzzle` / `CX35-C (No-Typed-Family-Choice)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.212769`
- `alpha_puzzle` / `CX35-C (No-Witness-Expansion)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.205793`
- `bug_trap` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.811590`
- `bug_trap` / `CX35-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.184120`
- `bug_trap` / `CX35-C (No-Typed-Family-Choice)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.172341`
- `bug_trap` / `CX35-C (No-Witness-Expansion)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.160198`
- `flange` / `CX3-D`: exp_delta=`-1421.000`, mean_time_overhead_ratio=`-0.769397`
- `flange` / `CX35-C (Full)`: exp_delta=`7.400`, mean_time_overhead_ratio=`-0.048192`
- `flange` / `CX35-C (No-Typed-Family-Choice)`: exp_delta=`7.400`, mean_time_overhead_ratio=`-0.049242`
- `flange` / `CX35-C (No-Witness-Expansion)`: exp_delta=`7.400`, mean_time_overhead_ratio=`-0.047389`
- `maze` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.796508`
- `maze` / `CX35-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.098283`
- `maze` / `CX35-C (No-Typed-Family-Choice)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.085534`
- `maze` / `CX35-C (No-Witness-Expansion)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.085022`
- `narrow_passage` / `CX3-D`: exp_delta=`-99.750`, mean_time_overhead_ratio=`-0.791204`
- `narrow_passage` / `CX35-C (Full)`: exp_delta=`-260.250`, mean_time_overhead_ratio=`0.072640`
- `narrow_passage` / `CX35-C (No-Typed-Family-Choice)`: exp_delta=`-260.250`, mean_time_overhead_ratio=`0.070081`
- `narrow_passage` / `CX35-C (No-Witness-Expansion)`: exp_delta=`-1.500`, mean_time_overhead_ratio=`0.032519`
- `parasol_misc` / `CX3-D`: exp_delta=`-10.500`, mean_time_overhead_ratio=`-0.823347`
- `parasol_misc` / `CX35-C (Full)`: exp_delta=`-28.167`, mean_time_overhead_ratio=`-0.118893`
- `parasol_misc` / `CX35-C (No-Typed-Family-Choice)`: exp_delta=`-28.167`, mean_time_overhead_ratio=`-0.123012`
- `parasol_misc` / `CX35-C (No-Witness-Expansion)`: exp_delta=`-28.167`, mean_time_overhead_ratio=`-0.124431`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`