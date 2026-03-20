# CX35-A Pilot V1

- protocol: frozen `CX34-A / Subtype-Specific Macro Rescue` parent on public evidence; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit
- research anchors:
  - Experience Graphs / reusable planning structure: Phillips et al., ICRA 2012 — https://www.ri.cmu.edu/pub_files/2012/5/icra12.pdf
  - Model preconditions / structural option applicability: Ravichandar et al., CoRL 2021 — https://proceedings.mlr.press/v164/ravichandar22a.html
  - Motion primitives in state lattices: Pivtoraiko & Kelly, iSAIRAS 2005
  - Motion planning with maneuver automata: Schouwenaars et al., ACC 2001 / hybrid systems maneuver automation line
- chosen params: `{'turn_bridge_max': 0.1, 'turn_focus_max': 0.36, 'rescue_bridge_max': 0.08, 'rescue_focus_min': 0.39, 'rescue_path_min': 0.99, 'rescue_budget': 1, 'suppress_bridge_min': 0.11, 'suppress_bridge_max': 0.13, 'suppress_focus_max': 0.31, 'suppress_path_min': 0.97, 'stubborn_bridge_min': 0.125, 'stubborn_focus_max': 0.34, 'stubborn_path_max': 0.97, 'maze_revisit_thr': 2, 'maze_stall_steps': 18, 'reverse_required_thr': 0.1, 'trap_thr': 0.54, 'progress_eps': 0.02, 'commit_fail_margin': 0.05, 'failure_ttl': 32, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24, 'min_hits': 2}`
- output root: `outputs/rs_p0cx35_a_pilot_v1`

## Public vs `CX3-D`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`420.389`, mean_time_overhead_ratio=`3.527234`
- `CX35-A (Full)`: success_delta_pp=`0.000`, exp_delta=`353.722`, mean_time_overhead_ratio=`3.428553`
- `CX35-A (No-Typed-Macro-Family)`: success_delta_pp=`0.000`, exp_delta=`412.722`, mean_time_overhead_ratio=`2.435140`
- `CX35-A (No-Witness)`: success_delta_pp=`0.000`, exp_delta=`434.278`, mean_time_overhead_ratio=`3.281847`

## Public Family Breakdown vs `CX3-D`
- `alpha_puzzle` / `CX34-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.323819`
- `alpha_puzzle` / `CX35-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`3.090074`
- `alpha_puzzle` / `CX35-A (No-Typed-Macro-Family)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.907721`
- `alpha_puzzle` / `CX35-A (No-Witness)`: exp_delta=`0.000`, mean_time_overhead_ratio=`3.092685`
- `bug_trap` / `CX34-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.307586`
- `bug_trap` / `CX35-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`3.265390`
- `bug_trap` / `CX35-A (No-Typed-Macro-Family)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.779542`
- `bug_trap` / `CX35-A (No-Witness)`: exp_delta=`0.000`, mean_time_overhead_ratio=`3.312458`
- `flange` / `CX34-A (Full)`: exp_delta=`1421.000`, mean_time_overhead_ratio=`3.336465`
- `flange` / `CX35-A (Full)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`3.074822`
- `flange` / `CX35-A (No-Typed-Macro-Family)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.283466`
- `flange` / `CX35-A (No-Witness)`: exp_delta=`1390.800`, mean_time_overhead_ratio=`3.021197`
- `maze` / `CX34-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`3.914200`
- `maze` / `CX35-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.371984`
- `maze` / `CX35-A (No-Typed-Macro-Family)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.756045`
- `maze` / `CX35-A (No-Witness)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.137295`
- `narrow_passage` / `CX34-A (Full)`: exp_delta=`99.750`, mean_time_overhead_ratio=`3.789361`
- `narrow_passage` / `CX35-A (Full)`: exp_delta=`-167.250`, mean_time_overhead_ratio=`4.085973`
- `narrow_passage` / `CX35-A (No-Typed-Macro-Family)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.639151`
- `narrow_passage` / `CX35-A (No-Witness)`: exp_delta=`262.500`, mean_time_overhead_ratio=`3.733738`
- `parasol_misc` / `CX34-A (Full)`: exp_delta=`10.500`, mean_time_overhead_ratio=`4.660825`
- `parasol_misc` / `CX35-A (Full)`: exp_delta=`-17.667`, mean_time_overhead_ratio=`3.916994`
- `parasol_misc` / `CX35-A (No-Typed-Macro-Family)`: exp_delta=`-17.667`, mean_time_overhead_ratio=`3.378734`
- `parasol_misc` / `CX35-A (No-Witness)`: exp_delta=`-31.167`, mean_time_overhead_ratio=`3.939714`

## Public vs `CX34-A (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-420.389`, mean_time_overhead_ratio=`-0.779115`
- `CX35-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-66.667`, mean_time_overhead_ratio=`-0.021797`
- `CX35-A (No-Typed-Macro-Family)`: success_delta_pp=`0.000`, exp_delta=`-7.667`, mean_time_overhead_ratio=`-0.241228`
- `CX35-A (No-Witness)`: success_delta_pp=`0.000`, exp_delta=`13.889`, mean_time_overhead_ratio=`-0.054203`

## Public Family Breakdown vs `CX34-A (Full)`
- `alpha_puzzle` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.812165`
- `alpha_puzzle` / `CX35-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.231741`
- `alpha_puzzle` / `CX35-A (No-Typed-Macro-Family)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.265993`
- `alpha_puzzle` / `CX35-A (No-Witness)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.231250`
- `bug_trap` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.811590`
- `bug_trap` / `CX35-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.196360`
- `bug_trap` / `CX35-A (No-Typed-Macro-Family)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.287898`
- `bug_trap` / `CX35-A (No-Witness)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.187492`
- `flange` / `CX3-D`: exp_delta=`-1421.000`, mean_time_overhead_ratio=`-0.769397`
- `flange` / `CX35-A (Full)`: exp_delta=`7.400`, mean_time_overhead_ratio=`-0.060335`
- `flange` / `CX35-A (No-Typed-Macro-Family)`: exp_delta=`7.400`, mean_time_overhead_ratio=`-0.242824`
- `flange` / `CX35-A (No-Witness)`: exp_delta=`-30.200`, mean_time_overhead_ratio=`-0.072702`
- `maze` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.796508`
- `maze` / `CX35-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.093155`
- `maze` / `CX35-A (No-Typed-Macro-Family)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.235675`
- `maze` / `CX35-A (No-Witness)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.045398`
- `narrow_passage` / `CX3-D`: exp_delta=`-99.750`, mean_time_overhead_ratio=`-0.791204`
- `narrow_passage` / `CX35-A (Full)`: exp_delta=`-267.000`, mean_time_overhead_ratio=`0.061931`
- `narrow_passage` / `CX35-A (No-Typed-Macro-Family)`: exp_delta=`-1.500`, mean_time_overhead_ratio=`-0.240159`
- `narrow_passage` / `CX35-A (No-Witness)`: exp_delta=`162.750`, mean_time_overhead_ratio=`-0.011614`
- `parasol_misc` / `CX3-D`: exp_delta=`-10.500`, mean_time_overhead_ratio=`-0.823347`
- `parasol_misc` / `CX35-A (Full)`: exp_delta=`-28.167`, mean_time_overhead_ratio=`-0.131400`
- `parasol_misc` / `CX35-A (No-Typed-Macro-Family)`: exp_delta=`-28.167`, mean_time_overhead_ratio=`-0.226485`
- `parasol_misc` / `CX35-A (No-Witness)`: exp_delta=`-41.667`, mean_time_overhead_ratio=`-0.127386`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`