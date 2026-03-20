# CX36-A Pilot V1

- protocol: frozen `CX35-B / Typed Family Macro Rescue` parent on public evidence; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit
- research anchors:
  - Model preconditions / structural applicability: Ravichandar et al., CoRL 2021 — https://proceedings.mlr.press/v164/ravichandar22a.html
  - Experience reuse / planning structure: Phillips et al., ICRA 2012 — https://www.ri.cmu.edu/pub_files/2012/5/icra12.pdf
  - Selective prediction / abstention: Geifman and El-Yaniv, ICML 2019 — https://proceedings.mlr.press/v97/geifman19a.html
  - Depression avoidance / event-triggered search control: Hernández et al., SoCS 2011 — https://ojs.aaai.org/index.php/SOCS/article/view/18315
- chosen params: `{'turn_bridge_max': 0.1, 'turn_focus_max': 0.36, 'rescue_bridge_max': 0.08, 'rescue_focus_min': 0.39, 'rescue_path_min': 0.99, 'rescue_budget': 1, 'suppress_bridge_min': 0.11, 'suppress_bridge_max': 0.13, 'suppress_focus_max': 0.31, 'suppress_path_min': 0.97, 'stubborn_bridge_min': 0.125, 'stubborn_focus_max': 0.34, 'stubborn_path_max': 0.97, 'macro_bridge_min': 0.078, 'macro_bridge_max': 0.095, 'macro_focus_min': 0.34, 'macro_focus_max': 0.37, 'macro_path_min': 0.97, 'macro_path_max': 1.01, 'maze_revisit_thr': 2, 'maze_stall_steps': 18, 'reverse_required_thr': 0.1, 'trap_thr': 0.54, 'progress_eps': 0.02, 'commit_fail_margin': 0.05, 'failure_ttl': 32, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24, 'min_hits': 2}`
- output root: `outputs/rs_p0cx36_a_pilot_v1`

## Public vs `CX3-D`
- `CX35-B (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.458320`
- `CX36-A (Full)`: success_delta_pp=`0.000`, exp_delta=`412.722`, mean_time_overhead_ratio=`2.496697`
- `CX36-A (No-Counterfactual-Contract)`: success_delta_pp=`0.000`, exp_delta=`412.722`, mean_time_overhead_ratio=`2.499537`
- `CX36-A (No-Trigger-Witness)`: success_delta_pp=`0.000`, exp_delta=`412.722`, mean_time_overhead_ratio=`2.496528`

## Public Family Breakdown vs `CX3-D`
- `alpha_puzzle` / `CX35-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.970550`
- `alpha_puzzle` / `CX36-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.954986`
- `alpha_puzzle` / `CX36-A (No-Counterfactual-Contract)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.994225`
- `alpha_puzzle` / `CX36-A (No-Trigger-Witness)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.954306`
- `bug_trap` / `CX35-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.850802`
- `bug_trap` / `CX36-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.813641`
- `bug_trap` / `CX36-A (No-Counterfactual-Contract)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.849484`
- `bug_trap` / `CX36-A (No-Trigger-Witness)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.795887`
- `flange` / `CX35-B (Full)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.303635`
- `flange` / `CX36-A (Full)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.326596`
- `flange` / `CX36-A (No-Counterfactual-Contract)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.329090`
- `flange` / `CX36-A (No-Trigger-Witness)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.323511`
- `maze` / `CX35-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.780985`
- `maze` / `CX36-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.786868`
- `maze` / `CX36-A (No-Counterfactual-Contract)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.814537`
- `maze` / `CX36-A (No-Trigger-Witness)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.813568`
- `narrow_passage` / `CX35-B (Full)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.651495`
- `narrow_passage` / `CX36-A (Full)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.680651`
- `narrow_passage` / `CX36-A (No-Counterfactual-Contract)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.685166`
- `narrow_passage` / `CX36-A (No-Trigger-Witness)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.684256`
- `parasol_misc` / `CX35-B (Full)`: exp_delta=`12.333`, mean_time_overhead_ratio=`3.560978`
- `parasol_misc` / `CX36-A (Full)`: exp_delta=`-17.667`, mean_time_overhead_ratio=`3.981866`
- `parasol_misc` / `CX36-A (No-Counterfactual-Contract)`: exp_delta=`-17.667`, mean_time_overhead_ratio=`3.973966`
- `parasol_misc` / `CX36-A (No-Trigger-Witness)`: exp_delta=`-17.667`, mean_time_overhead_ratio=`4.000302`

## Public vs `CX35-B (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.710842`
- `CX36-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-10.000`, mean_time_overhead_ratio=`0.011097`
- `CX36-A (No-Counterfactual-Contract)`: success_delta_pp=`0.000`, exp_delta=`-10.000`, mean_time_overhead_ratio=`0.011918`
- `CX36-A (No-Trigger-Witness)`: success_delta_pp=`0.000`, exp_delta=`-10.000`, mean_time_overhead_ratio=`0.011048`

## Public Family Breakdown vs `CX35-B (Full)`
- `alpha_puzzle` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.748146`
- `alpha_puzzle` / `CX36-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.003920`
- `alpha_puzzle` / `CX36-A (No-Counterfactual-Contract)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.005963`
- `alpha_puzzle` / `CX36-A (No-Trigger-Witness)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.004091`
- `bug_trap` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.740314`
- `bug_trap` / `CX36-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.009650`
- `bug_trap` / `CX36-A (No-Counterfactual-Contract)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.000342`
- `bug_trap` / `CX36-A (No-Trigger-Witness)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.014261`
- `flange` / `CX3-D`: exp_delta=`-1428.400`, mean_time_overhead_ratio=`-0.697303`
- `flange` / `CX36-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.006950`
- `flange` / `CX36-A (No-Counterfactual-Contract)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.007705`
- `flange` / `CX36-A (No-Trigger-Witness)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.006016`
- `maze` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.735519`
- `maze` / `CX36-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.001556`
- `maze` / `CX36-A (No-Counterfactual-Contract)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.008874`
- `maze` / `CX36-A (No-Trigger-Witness)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.008618`
- `narrow_passage` / `CX3-D`: exp_delta=`-98.250`, mean_time_overhead_ratio=`-0.726140`
- `narrow_passage` / `CX36-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.007985`
- `narrow_passage` / `CX36-A (No-Counterfactual-Contract)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.009221`
- `narrow_passage` / `CX36-A (No-Trigger-Witness)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.008972`
- `parasol_misc` / `CX3-D`: exp_delta=`-12.333`, mean_time_overhead_ratio=`-0.780749`
- `parasol_misc` / `CX36-A (Full)`: exp_delta=`-30.000`, mean_time_overhead_ratio=`0.092280`
- `parasol_misc` / `CX36-A (No-Counterfactual-Contract)`: exp_delta=`-30.000`, mean_time_overhead_ratio=`0.090548`
- `parasol_misc` / `CX36-A (No-Trigger-Witness)`: exp_delta=`-30.000`, mean_time_overhead_ratio=`0.096322`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`