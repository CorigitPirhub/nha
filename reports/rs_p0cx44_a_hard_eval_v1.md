# P0-CX44-A Hard Eval V1

- protocol: frozen hard-test evaluation; no retuning after public selection
- chosen json: `outputs/rs_p0cx44_a_pilot_v1/chosen.json`
- parent chosen json: `outputs/rs_p0cx34_a_pilot_v1/chosen.json`
- compat chosen json: `outputs/rs_p0cx41_b_pilot_v1/chosen.json`
- hard root: `data/benchmark/rs_root_hard_v2/test`

## Hard Benchmark vs `CX3-D`
- `CX34-A (Full)`: success_delta_pp=`2.740`, exp_delta=`196.548`, mean_time_overhead_ratio=`2.583531`, path_delta=`-1.179`
- `CX41-B (Full)`: success_delta_pp=`2.740`, exp_delta=`196.548`, mean_time_overhead_ratio=`3.953298`, path_delta=`-1.179`
- `CX44-A (Full)`: success_delta_pp=`2.740`, exp_delta=`196.589`, mean_time_overhead_ratio=`1.966899`, path_delta=`-1.179`
- `CX44-A (No-Witness-Transfer)`: success_delta_pp=`2.740`, exp_delta=`196.548`, mean_time_overhead_ratio=`1.515820`, path_delta=`-1.179`
- `CX44-A (Proxy-Only-Negative)`: success_delta_pp=`1.370`, exp_delta=`103.589`, mean_time_overhead_ratio=`1.379886`, path_delta=`-0.781`

## Hard Benchmark vs `CX34-A (Full)`
- `CX3-D`: success_delta_pp=`-2.740`, exp_delta=`-196.548`, mean_time_overhead_ratio=`-0.720946`, path_delta=`1.179`
- `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.382239`, path_delta=`0.000`
- `CX44-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.041`, mean_time_overhead_ratio=`-0.172074`, path_delta=`0.000`
- `CX44-A (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.297949`, path_delta=`0.000`
- `CX44-A (Proxy-Only-Negative)`: success_delta_pp=`-1.370`, exp_delta=`-92.959`, mean_time_overhead_ratio=`-0.335882`, path_delta=`0.397`

## Hard Benchmark vs `CX41-B (Full)`
- `CX3-D`: success_delta_pp=`-2.740`, exp_delta=`-196.548`, mean_time_overhead_ratio=`-0.798114`, path_delta=`1.179`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.276536`, path_delta=`0.000`
- `CX44-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.041`, mean_time_overhead_ratio=`-0.401025`, path_delta=`0.000`
- `CX44-A (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.492092`, path_delta=`0.000`
- `CX44-A (Proxy-Only-Negative)`: success_delta_pp=`-1.370`, exp_delta=`-92.959`, mean_time_overhead_ratio=`-0.519535`, path_delta=`0.397`

## Hard Family Breakdown vs `CX34-A (Full)`
- `alpha_puzzle` / `CX3-D`: success_delta_pp=`-9.091`, exp_delta=`-87.364`, mean_time_overhead_ratio=`-0.726843`, path_delta=`20.510`
- `alpha_puzzle` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.507839`, path_delta=`0.000`
- `alpha_puzzle` / `CX44-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.273`, mean_time_overhead_ratio=`-0.005891`, path_delta=`0.000`
- `alpha_puzzle` / `CX44-A (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.297957`, path_delta=`0.000`
- `alpha_puzzle` / `CX44-A (Proxy-Only-Negative)`: success_delta_pp=`-9.091`, exp_delta=`-87.364`, mean_time_overhead_ratio=`-0.353376`, path_delta=`20.510`
- `bug_trap` / `CX3-D`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.729939`, path_delta=`0.000`
- `bug_trap` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.406393`, path_delta=`0.000`
- `bug_trap` / `CX44-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.090151`, path_delta=`0.000`
- `bug_trap` / `CX44-A (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.293785`, path_delta=`0.000`
- `bug_trap` / `CX44-A (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.367102`, path_delta=`0.000`
- `deadend_labyrinth` / `CX3-D`: success_delta_pp=`0.000`, exp_delta=`361.100`, mean_time_overhead_ratio=`-0.743430`, path_delta=`-0.452`
- `deadend_labyrinth` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.187227`, path_delta=`0.000`
- `deadend_labyrinth` / `CX44-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.289160`, path_delta=`0.000`
- `deadend_labyrinth` / `CX44-A (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.300415`, path_delta=`0.000`
- `deadend_labyrinth` / `CX44-A (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`329.600`, mean_time_overhead_ratio=`-0.390270`, path_delta=`-0.280`
- `flange` / `CX3-D`: success_delta_pp=`0.000`, exp_delta=`41.538`, mean_time_overhead_ratio=`-0.727274`, path_delta=`0.230`
- `flange` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.446482`, path_delta=`0.000`
- `flange` / `CX44-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.247159`, path_delta=`0.000`
- `flange` / `CX44-A (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.299744`, path_delta=`0.000`
- `flange` / `CX44-A (Proxy-Only-Negative)`: success_delta_pp=`7.692`, exp_delta=`-132.000`, mean_time_overhead_ratio=`-0.344215`, path_delta=`-8.839`
- `maze` / `CX3-D`: success_delta_pp=`-9.091`, exp_delta=`-1274.455`, mean_time_overhead_ratio=`-0.693895`, path_delta=`0.499`
- `maze` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.243432`, path_delta=`0.000`
- `maze` / `CX44-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.293564`, path_delta=`0.000`
- `maze` / `CX44-A (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.298238`, path_delta=`0.000`
- `maze` / `CX44-A (Proxy-Only-Negative)`: success_delta_pp=`-9.091`, exp_delta=`-590.727`, mean_time_overhead_ratio=`-0.257213`, path_delta=`1.022`
- `narrow_passage` / `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-273.615`, mean_time_overhead_ratio=`-0.703338`, path_delta=`0.038`
- `narrow_passage` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.017379`, path_delta=`0.000`
- `narrow_passage` / `CX44-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.304053`, path_delta=`0.000`
- `narrow_passage` / `CX44-A (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.303951`, path_delta=`0.000`
- `narrow_passage` / `CX44-A (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`-67.846`, mean_time_overhead_ratio=`-0.346386`, path_delta=`-0.083`
- `parasol_misc` / `CX3-D`: success_delta_pp=`0.000`, exp_delta=`9.500`, mean_time_overhead_ratio=`-0.773399`, path_delta=`0.056`
- `parasol_misc` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.072411`, path_delta=`0.000`
- `parasol_misc` / `CX44-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.333524`, path_delta=`0.000`
- `parasol_misc` / `CX44-A (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.296167`, path_delta=`0.000`
- `parasol_misc` / `CX44-A (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`-6.250`, mean_time_overhead_ratio=`-0.370932`, path_delta=`0.053`