# P0-CX44-B Hard Eval V1

- protocol: frozen hard-test evaluation; no retuning after public selection
- chosen json: `outputs/rs_p0cx44_b_pilot_v1/chosen.json`
- parent chosen json: `outputs/rs_p0cx34_a_pilot_v1/chosen.json`
- compat chosen json: `outputs/rs_p0cx41_b_pilot_v1/chosen.json`
- hard root: `data/benchmark/rs_root_hard_v2_order_audit_subset_v1/test`

## Hard Benchmark vs `CX3-D`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`112.357`, mean_time_overhead_ratio=`2.561120`, path_delta=`-0.071`
- `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`112.357`, mean_time_overhead_ratio=`4.551551`, path_delta=`-0.071`
- `CX44-B (Full)`: success_delta_pp=`0.000`, exp_delta=`112.357`, mean_time_overhead_ratio=`2.564099`, path_delta=`-0.071`
- `CX44-B (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`112.357`, mean_time_overhead_ratio=`2.560227`, path_delta=`-0.071`
- `CX44-B (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`-3.429`, mean_time_overhead_ratio=`2.588926`, path_delta=`-0.087`

## Hard Benchmark vs `CX34-A (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-112.357`, mean_time_overhead_ratio=`-0.719189`, path_delta=`0.071`
- `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.558934`, path_delta=`0.000`
- `CX44-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.000837`, path_delta=`0.000`
- `CX44-B (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.000251`, path_delta=`0.000`
- `CX44-B (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`-115.786`, mean_time_overhead_ratio=`0.007808`, path_delta=`-0.016`

## Hard Benchmark vs `CX41-B (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-112.357`, mean_time_overhead_ratio=`-0.819870`, path_delta=`0.071`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.358536`, path_delta=`0.000`
- `CX44-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.357999`, path_delta=`0.000`
- `CX44-B (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.358697`, path_delta=`0.000`
- `CX44-B (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`-115.786`, mean_time_overhead_ratio=`-0.353527`, path_delta=`-0.016`

## Hard Family Breakdown vs `CX34-A (Full)`
- `alpha_puzzle` / `CX3-D`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.747589`, path_delta=`0.000`
- `alpha_puzzle` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.597134`, path_delta=`0.000`
- `alpha_puzzle` / `CX44-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.052196`, path_delta=`0.000`
- `alpha_puzzle` / `CX44-B (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.016121`, path_delta=`0.000`
- `alpha_puzzle` / `CX44-B (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.020564`, path_delta=`0.000`
- `bug_trap` / `CX3-D`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.759378`, path_delta=`0.000`
- `bug_trap` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.621035`, path_delta=`0.000`
- `bug_trap` / `CX44-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.075073`, path_delta=`0.000`
- `bug_trap` / `CX44-B (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.002918`, path_delta=`0.000`
- `bug_trap` / `CX44-B (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.002553`, path_delta=`0.000`
- `deadend_labyrinth` / `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-16.500`, mean_time_overhead_ratio=`-0.657065`, path_delta=`0.012`
- `deadend_labyrinth` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.400735`, path_delta=`0.000`
- `deadend_labyrinth` / `CX44-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.013704`, path_delta=`0.000`
- `deadend_labyrinth` / `CX44-B (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.009853`, path_delta=`0.000`
- `deadend_labyrinth` / `CX44-B (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`-1.500`, mean_time_overhead_ratio=`-0.079005`, path_delta=`0.000`
- `flange` / `CX3-D`: success_delta_pp=`0.000`, exp_delta=`227.000`, mean_time_overhead_ratio=`-0.736776`, path_delta=`0.460`
- `flange` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.398556`, path_delta=`0.000`
- `flange` / `CX44-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.002576`, path_delta=`0.000`
- `flange` / `CX44-B (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.006758`, path_delta=`0.000`
- `flange` / `CX44-B (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.006392`, path_delta=`0.000`
- `maze` / `CX3-D`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.716044`, path_delta=`0.000`
- `maze` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.790707`, path_delta=`0.000`
- `maze` / `CX44-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.000406`, path_delta=`0.000`
- `maze` / `CX44-B (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.000325`, path_delta=`0.000`
- `maze` / `CX44-B (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.000651`, path_delta=`0.000`
- `narrow_passage` / `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-1012.500`, mean_time_overhead_ratio=`-0.686510`, path_delta=`0.046`
- `narrow_passage` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.486350`, path_delta=`0.000`
- `narrow_passage` / `CX44-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.001748`, path_delta=`0.000`
- `narrow_passage` / `CX44-B (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.012746`, path_delta=`0.000`
- `narrow_passage` / `CX44-B (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`-809.000`, mean_time_overhead_ratio=`0.053138`, path_delta=`-0.064`
- `parasol_misc` / `CX3-D`: success_delta_pp=`0.000`, exp_delta=`15.500`, mean_time_overhead_ratio=`-0.777585`, path_delta=`0.000`
- `parasol_misc` / `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.175230`, path_delta=`0.000`
- `parasol_misc` / `CX44-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.073845`, path_delta=`0.000`
- `parasol_misc` / `CX44-B (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.012990`, path_delta=`0.000`
- `parasol_misc` / `CX44-B (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.087427`, path_delta=`0.000`