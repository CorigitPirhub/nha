# P0-CX43-D Hard Eval V1

- protocol: frozen hard-test evaluation; no retuning after public selection
- chosen json: `outputs/rs_p0cx43_d_pilot_v1/chosen.json`
- parent chosen json: `outputs/rs_p0cx34_a_pilot_v1/chosen.json`
- compat chosen json: `outputs/rs_p0cx41_b_pilot_v1/chosen.json`
- hard root: `data/benchmark/rs_root_hard_v2/test`

## Hard Benchmark vs `CX3-D`
- `CX34-A (Full)`: success_delta_pp=`2.740`, exp_delta=`196.548`, mean_time_overhead_ratio=`2.639501`, path_delta=`-1.179`
- `CX41-B (Full)`: success_delta_pp=`2.740`, exp_delta=`196.548`, mean_time_overhead_ratio=`4.648226`, path_delta=`-1.179`
- `CX43-D (Full)`: success_delta_pp=`2.740`, exp_delta=`196.548`, mean_time_overhead_ratio=`2.686819`, path_delta=`-1.179`
- `CX43-D (No-Rank-Release)`: success_delta_pp=`2.740`, exp_delta=`196.548`, mean_time_overhead_ratio=`2.673396`, path_delta=`-1.179`
- `CX43-D (Proxy-Only)`: success_delta_pp=`0.000`, exp_delta=`91.397`, mean_time_overhead_ratio=`1.123827`, path_delta=`-0.045`

## Hard Benchmark vs `CX34-A (Full)`
- `CX3-D`: success_delta_pp=`-2.740`, exp_delta=`-196.548`, mean_time_overhead_ratio=`-0.725237`, path_delta=`1.179`
- `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.551923`, path_delta=`0.000`
- `CX43-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.013001`, path_delta=`0.000`
- `CX43-D (No-Rank-Release)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.009313`, path_delta=`0.000`
- `CX43-D (Proxy-Only)`: success_delta_pp=`-2.740`, exp_delta=`-105.151`, mean_time_overhead_ratio=`-0.416451`, path_delta=`1.133`

## Hard Benchmark vs `CX41-B (Full)`
- `CX3-D`: success_delta_pp=`-2.740`, exp_delta=`-196.548`, mean_time_overhead_ratio=`-0.822953`, path_delta=`1.179`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.355638`, path_delta=`0.000`
- `CX43-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.347261`, path_delta=`0.000`
- `CX43-D (No-Rank-Release)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.349637`, path_delta=`0.000`
- `CX43-D (Proxy-Only)`: success_delta_pp=`-2.740`, exp_delta=`-105.151`, mean_time_overhead_ratio=`-0.623983`, path_delta=`1.133`

## Hard Family Breakdown vs `CX34-A (Full)`
- `alpha_puzzle` / `CX3-D`: success_delta_pp=`-9.091`, exp_delta=`-87.364`, mean_time_overhead_ratio=`-0.728484`, path_delta=`20.510`
- `alpha_puzzle` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.517369`, path_delta=`0.000`
- `alpha_puzzle` / `CX43-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.013705`, path_delta=`0.000`
- `alpha_puzzle` / `CX43-D (No-Rank-Release)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.013179`, path_delta=`0.000`
- `alpha_puzzle` / `CX43-D (Proxy-Only)`: success_delta_pp=`0.000`, exp_delta=`111.727`, mean_time_overhead_ratio=`-0.426890`, path_delta=`-0.055`
- `bug_trap` / `CX3-D`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.735155`, path_delta=`0.000`
- `bug_trap` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.400986`, path_delta=`0.000`
- `bug_trap` / `CX43-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.012900`, path_delta=`0.000`
- `bug_trap` / `CX43-D (No-Rank-Release)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.010623`, path_delta=`0.000`
- `bug_trap` / `CX43-D (Proxy-Only)`: success_delta_pp=`0.000`, exp_delta=`0.273`, mean_time_overhead_ratio=`-0.425321`, path_delta=`0.000`
- `deadend_labyrinth` / `CX3-D`: success_delta_pp=`0.000`, exp_delta=`361.100`, mean_time_overhead_ratio=`-0.747178`, path_delta=`-0.452`
- `deadend_labyrinth` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.699223`, path_delta=`0.000`
- `deadend_labyrinth` / `CX43-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.017421`, path_delta=`0.000`
- `deadend_labyrinth` / `CX43-D (No-Rank-Release)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.012495`, path_delta=`0.000`
- `deadend_labyrinth` / `CX43-D (Proxy-Only)`: success_delta_pp=`0.000`, exp_delta=`312.200`, mean_time_overhead_ratio=`-0.462023`, path_delta=`-0.443`
- `flange` / `CX3-D`: success_delta_pp=`0.000`, exp_delta=`41.538`, mean_time_overhead_ratio=`-0.732153`, path_delta=`0.230`
- `flange` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.530727`, path_delta=`0.000`
- `flange` / `CX43-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.011089`, path_delta=`0.000`
- `flange` / `CX43-D (No-Rank-Release)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.008437`, path_delta=`0.000`
- `flange` / `CX43-D (Proxy-Only)`: success_delta_pp=`0.000`, exp_delta=`150.385`, mean_time_overhead_ratio=`-0.431199`, path_delta=`-0.074`
- `maze` / `CX3-D`: success_delta_pp=`-9.091`, exp_delta=`-1274.455`, mean_time_overhead_ratio=`-0.699700`, path_delta=`0.499`
- `maze` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.780450`, path_delta=`0.000`
- `maze` / `CX43-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.015114`, path_delta=`0.000`
- `maze` / `CX43-D (No-Rank-Release)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.003547`, path_delta=`0.000`
- `maze` / `CX43-D (Proxy-Only)`: success_delta_pp=`-18.182`, exp_delta=`-1002.364`, mean_time_overhead_ratio=`-0.373465`, path_delta=`0.308`
- `narrow_passage` / `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-273.615`, mean_time_overhead_ratio=`-0.707484`, path_delta=`0.038`
- `narrow_passage` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.271016`, path_delta=`0.000`
- `narrow_passage` / `CX43-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.004604`, path_delta=`0.000`
- `narrow_passage` / `CX43-D (No-Rank-Release)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.011623`, path_delta=`0.000`
- `narrow_passage` / `CX43-D (Proxy-Only)`: success_delta_pp=`0.000`, exp_delta=`-213.923`, mean_time_overhead_ratio=`-0.371395`, path_delta=`-0.089`
- `parasol_misc` / `CX3-D`: success_delta_pp=`0.000`, exp_delta=`9.500`, mean_time_overhead_ratio=`-0.773789`, path_delta=`0.056`
- `parasol_misc` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.114918`, path_delta=`0.000`
- `parasol_misc` / `CX43-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.009302`, path_delta=`0.000`
- `parasol_misc` / `CX43-D (No-Rank-Release)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.004352`, path_delta=`0.000`
- `parasol_misc` / `CX43-D (Proxy-Only)`: success_delta_pp=`0.000`, exp_delta=`-44.500`, mean_time_overhead_ratio=`-0.324383`, path_delta=`0.000`