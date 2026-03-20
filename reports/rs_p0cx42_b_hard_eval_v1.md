# P0-CX42-B Hard Eval V1

- protocol: frozen hard-test evaluation; no retuning after public selection
- chosen json: `outputs/rs_p0cx42_b_pilot_v1/chosen.json`
- parent chosen json: `outputs/rs_p0cx34_a_pilot_v1/chosen.json`
- compat chosen json: `outputs/rs_p0cx41_b_pilot_v1/chosen.json`
- hard root: `data/benchmark/rs_root_hard_v2/test`
- device: `cuda`
- fixed cap: `20000`
- inputs sha256: `outputs/rs_p0cx42_b_hard_eval_v1/inputs_sha256.json`

## Hard Benchmark vs `CX3-D`
- `CX34-A (Full)`: success_delta_pp=`2.740`, exp_delta=`196.548`, mean_time_overhead_ratio=`2.361795`, path_delta=`-1.179`
- `CX41-B (Full)`: success_delta_pp=`2.740`, exp_delta=`196.548`, mean_time_overhead_ratio=`2.703178`, path_delta=`-1.179`
- `CX42-B (Full)`: success_delta_pp=`2.740`, exp_delta=`196.548`, mean_time_overhead_ratio=`1.387461`, path_delta=`-1.179`

## Hard Benchmark vs `CX34-A (Full)`
- `CX3-D`: success_delta_pp=`-2.740`, exp_delta=`-196.548`, mean_time_overhead_ratio=`-0.702540`, path_delta=`1.179`
- `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.101548`, path_delta=`0.000`
- `CX42-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.289825`, path_delta=`0.000`

## Hard Benchmark vs `CX41-B (Full)`
- `CX3-D`: success_delta_pp=`-2.740`, exp_delta=`-196.548`, mean_time_overhead_ratio=`-0.729962`, path_delta=`1.179`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.092187`, path_delta=`0.000`
- `CX42-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.355294`, path_delta=`0.000`

## Hard Family Breakdown vs `CX34-A (Full)`
- `alpha_puzzle` / `CX3-D`: success_delta_pp=`-9.091`, exp_delta=`-87.364`, mean_time_overhead_ratio=`-0.719862`, path_delta=`20.510`
- `alpha_puzzle` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.022482`, path_delta=`0.000`
- `alpha_puzzle` / `CX42-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.322809`, path_delta=`0.000`
- `bug_trap` / `CX3-D`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.725850`, path_delta=`0.000`
- `bug_trap` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.054303`, path_delta=`0.000`
- `bug_trap` / `CX42-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.324883`, path_delta=`0.000`
- `deadend_labyrinth` / `CX3-D`: success_delta_pp=`0.000`, exp_delta=`361.100`, mean_time_overhead_ratio=`-0.608544`, path_delta=`-0.452`
- `deadend_labyrinth` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.724617`, path_delta=`0.000`
- `deadend_labyrinth` / `CX42-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.018866`, path_delta=`0.000`
- `flange` / `CX3-D`: success_delta_pp=`0.000`, exp_delta=`41.538`, mean_time_overhead_ratio=`-0.723269`, path_delta=`0.230`
- `flange` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.038818`, path_delta=`0.000`
- `flange` / `CX42-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.320369`, path_delta=`0.000`
- `maze` / `CX3-D`: success_delta_pp=`-9.091`, exp_delta=`-1274.455`, mean_time_overhead_ratio=`-0.640836`, path_delta=`0.499`
- `maze` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.405148`, path_delta=`0.000`
- `maze` / `CX42-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.214727`, path_delta=`0.000`
- `narrow_passage` / `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-273.615`, mean_time_overhead_ratio=`-0.697709`, path_delta=`0.038`
- `narrow_passage` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.140641`, path_delta=`0.000`
- `narrow_passage` / `CX42-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.322676`, path_delta=`0.000`
- `parasol_misc` / `CX3-D`: success_delta_pp=`0.000`, exp_delta=`9.500`, mean_time_overhead_ratio=`-0.767834`, path_delta=`0.056`
- `parasol_misc` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.414099`, path_delta=`0.000`
- `parasol_misc` / `CX42-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.319407`, path_delta=`0.000`