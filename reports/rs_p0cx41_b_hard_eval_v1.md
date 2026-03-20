# P0-CX41-B Hard Eval V1

- protocol: frozen hard-test evaluation; no retuning after public selection
- chosen json: `outputs/rs_p0cx41_b_pilot_v1/chosen.json`
- parent chosen json: `outputs/rs_p0cx40_a_pilot_v1/chosen.json`
- hard root: `data/benchmark/rs_root_hard_v2/test`
- device: `cuda`
- fixed cap: `20000`
- inputs sha256: `outputs/rs_p0cx41_b_hard_eval_v1/inputs_sha256.json`

## Hard Benchmark vs `CX3-D`
- `CX40-A (Full)`: success_delta_pp=`2.740`, exp_delta=`196.548`, mean_time_overhead_ratio=`11.932472`, path_delta=`-1.179`
- `CX41-B (Full)`: success_delta_pp=`2.740`, exp_delta=`196.548`, mean_time_overhead_ratio=`4.528595`, path_delta=`-1.179`

## Hard Benchmark vs `CX40-A (Full)`
- `CX3-D`: success_delta_pp=`-2.740`, exp_delta=`-196.548`, mean_time_overhead_ratio=`-0.922675`, path_delta=`1.179`
- `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.572503`, path_delta=`0.000`

## Hard Family Breakdown vs `CX3-D`
- `alpha_puzzle` / `CX40-A (Full)`: success_delta_pp=`9.091`, exp_delta=`87.364`, mean_time_overhead_ratio=`9.630206`, path_delta=`-20.510`
- `alpha_puzzle` / `CX41-B (Full)`: success_delta_pp=`9.091`, exp_delta=`87.364`, mean_time_overhead_ratio=`4.501512`, path_delta=`-20.510`
- `bug_trap` / `CX40-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`6.853424`, path_delta=`0.000`
- `bug_trap` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`4.199594`, path_delta=`0.000`
- `deadend_labyrinth` / `CX40-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-361.100`, mean_time_overhead_ratio=`13.865528`, path_delta=`0.452`
- `deadend_labyrinth` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`-361.100`, mean_time_overhead_ratio=`5.403166`, path_delta=`0.452`
- `flange` / `CX40-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-41.538`, mean_time_overhead_ratio=`10.861095`, path_delta=`-0.230`
- `flange` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`-41.538`, mean_time_overhead_ratio=`4.618212`, path_delta=`-0.230`
- `maze` / `CX40-A (Full)`: success_delta_pp=`9.091`, exp_delta=`1274.455`, mean_time_overhead_ratio=`20.544927`, path_delta=`-0.499`
- `maze` / `CX41-B (Full)`: success_delta_pp=`9.091`, exp_delta=`1274.455`, mean_time_overhead_ratio=`4.754461`, path_delta=`-0.499`
- `narrow_passage` / `CX40-A (Full)`: success_delta_pp=`0.000`, exp_delta=`273.615`, mean_time_overhead_ratio=`5.920842`, path_delta=`-0.038`
- `narrow_passage` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`273.615`, mean_time_overhead_ratio=`3.260502`, path_delta=`-0.038`
- `parasol_misc` / `CX40-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-9.500`, mean_time_overhead_ratio=`23.378352`, path_delta=`-0.056`
- `parasol_misc` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`-9.500`, mean_time_overhead_ratio=`8.112890`, path_delta=`-0.056`

## Hard Family Breakdown vs `CX40-A (Full)`
- `alpha_puzzle` / `CX3-D`: success_delta_pp=`-9.091`, exp_delta=`-87.364`, mean_time_overhead_ratio=`-0.905928`, path_delta=`20.510`
- `alpha_puzzle` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.482464`, path_delta=`0.000`
- `bug_trap` / `CX3-D`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.872667`, path_delta=`0.000`
- `bug_trap` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.337920`, path_delta=`0.000`
- `deadend_labyrinth` / `CX3-D`: success_delta_pp=`0.000`, exp_delta=`361.100`, mean_time_overhead_ratio=`-0.932730`, path_delta=`-0.452`
- `deadend_labyrinth` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.569261`, path_delta=`0.000`
- `flange` / `CX3-D`: success_delta_pp=`0.000`, exp_delta=`41.538`, mean_time_overhead_ratio=`-0.915691`, path_delta=`0.230`
- `flange` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.526333`, path_delta=`0.000`
- `maze` / `CX3-D`: success_delta_pp=`-9.091`, exp_delta=`-1274.455`, mean_time_overhead_ratio=`-0.953585`, path_delta=`0.499`
- `maze` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.732909`, path_delta=`0.000`
- `narrow_passage` / `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-273.615`, mean_time_overhead_ratio=`-0.855509`, path_delta=`0.038`
- `narrow_passage` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.384395`, path_delta=`0.000`
- `parasol_misc` / `CX3-D`: success_delta_pp=`0.000`, exp_delta=`9.500`, mean_time_overhead_ratio=`-0.958980`, path_delta=`0.056`
- `parasol_misc` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.626189`, path_delta=`0.000`