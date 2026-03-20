# P0-CX35-B Hard Eval V1

- protocol: frozen hard-test evaluation; no retuning after public selection
- chosen json: `outputs/rs_p0cx35_rerun_v2/rs_p0cx35_b_pilot_v1/chosen.json`
- hard root: `data/benchmark/rs_root_hard_v2/test`
- device: `cuda`
- fixed cap: `20000`
- inputs sha256: `outputs/rs_p0cx35_b_hard_eval_v1/inputs_sha256.json`

## Hard Benchmark vs `CX3-D`
- `CX35-B (Full)`: success_delta_pp=`2.740`, exp_delta=`196.548`, mean_time_overhead_ratio=`2.562212`, path_delta=`-1.179`

## Hard Family Breakdown vs `CX3-D`
- `alpha_puzzle` / `CX35-B (Full)`: success_delta_pp=`9.091`, exp_delta=`87.364`, mean_time_overhead_ratio=`2.614312`, path_delta=`-20.510`
- `bug_trap` / `CX35-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`2.669006`, path_delta=`0.000`
- `deadend_labyrinth` / `CX35-B (Full)`: success_delta_pp=`0.000`, exp_delta=`-361.100`, mean_time_overhead_ratio=`2.874310`, path_delta=`0.452`
- `flange` / `CX35-B (Full)`: success_delta_pp=`0.000`, exp_delta=`-41.538`, mean_time_overhead_ratio=`2.664085`, path_delta=`-0.230`
- `maze` / `CX35-B (Full)`: success_delta_pp=`9.091`, exp_delta=`1274.455`, mean_time_overhead_ratio=`2.259977`, path_delta=`-0.499`
- `narrow_passage` / `CX35-B (Full)`: success_delta_pp=`0.000`, exp_delta=`273.615`, mean_time_overhead_ratio=`2.354639`, path_delta=`-0.038`
- `parasol_misc` / `CX35-B (Full)`: success_delta_pp=`0.000`, exp_delta=`-9.500`, mean_time_overhead_ratio=`3.320062`, path_delta=`-0.056`

## Verdict
- `CX35-B` preserves the accepted `CX34-A` hard-test overall result almost exactly while slightly reducing runtime overhead
- the hard-family shape is unchanged in substance: `maze` / `narrow_passage` stay strongly positive, while `deadend_labyrinth` / `flange` / `parasol_misc` remain the unresolved negatives
- therefore `CX35-B` is best read as a successful mechanism-object refactor of the accepted slice, not yet as a hard-generalization upgrade
