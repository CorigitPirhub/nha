# CX20-A Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow` evaluation; hard-test is consumed when public overall turns positive and `flange` stays non-negative
- chosen params: `{'cost_gain': 0.02, 'viability_gain': 0.1, 'reverse_gain': 0.06, 'trap_escape_gain': 0.04, 'oracle_gain': 0.04, 'stride_cells': 2, 'yaw_stride': 2, 'horizon_steps': 5}`
- output root: `outputs/rs_p0cx20_a_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`-14.286`
- exp_delta=`-827.429`
- mean_time_overhead_ratio=`3.307039`

## Calib Family Breakdown
- `flange`: exp_delta=`2436.000`, mean_time_overhead_ratio=`2.141763`
- `maze`: exp_delta=`-2738.000`, mean_time_overhead_ratio=`3.711840`
- `narrow_passage`: exp_delta=`181.500`, mean_time_overhead_ratio=`2.579749`
- `parasol_misc`: exp_delta=`-377.000`, mean_time_overhead_ratio=`4.712489`

## Public Parasol vs `CX3-D`
- `exp3` / `CX20-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-83.333`, mean_time_overhead_ratio=`3.232609`
- `exp3` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-130.333`, mean_time_overhead_ratio=`0.042909`
- `exp4` / `CX20-A (Full)`: success_delta_pp=`0.000`, exp_delta=`52.000`, mean_time_overhead_ratio=`3.033387`
- `exp4` / `CX20-A (No-MultiHead)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.022069`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.028351`

## Public `exp4` Family Breakdown
- `alpha_puzzle` / `CX20-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-1.000`, mean_time_overhead_ratio=`3.347800`
- `alpha_puzzle` / `CX20-A (No-MultiHead)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.003275`
- `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.050884`
- `bug_trap` / `CX20-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`2.961505`
- `bug_trap` / `CX20-A (No-MultiHead)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.033746`
- `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.219008`
- `flange` / `CX20-A (Full)`: success_delta_pp=`0.000`, exp_delta=`173.800`, mean_time_overhead_ratio=`3.003991`
- `flange` / `CX20-A (No-MultiHead)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.023960`
- `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`42.600`, mean_time_overhead_ratio=`-0.002614`
- `maze` / `CX20-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`3.101102`
- `maze` / `CX20-A (No-MultiHead)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.011343`
- `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.030750`
- `narrow_passage` / `CX20-A (Full)`: success_delta_pp=`0.000`, exp_delta=`117.750`, mean_time_overhead_ratio=`3.019717`
- `narrow_passage` / `CX20-A (No-MultiHead)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.018633`
- `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.006491`
- `parasol_misc` / `CX20-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-67.167`, mean_time_overhead_ratio=`3.716763`
- `parasol_misc` / `CX20-A (No-MultiHead)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.020400`
- `parasol_misc` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-451.500`, mean_time_overhead_ratio=`0.950310`

## Hard Benchmark vs `CX3-D`
- `CX20-A (Full)`: success_delta_pp=`-1.370`, exp_delta=`23.068`, mean_time_overhead_ratio=`3.921329`, path_delta=`1.110`
- `Hybrid A* (RS)`: success_delta_pp=`1.370`, exp_delta=`214.973`, mean_time_overhead_ratio=`-0.062391`, path_delta=`-0.626`

## Hard Family Breakdown
- `alpha_puzzle` / `CX20-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-0.091`, mean_time_overhead_ratio=`4.177267`
- `bug_trap` / `CX20-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`4.049976`
- `deadend_labyrinth` / `CX20-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-141.600`, mean_time_overhead_ratio=`3.825139`
- `flange` / `CX20-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-120.538`, mean_time_overhead_ratio=`4.360644`
- `maze` / `CX20-A (Full)`: success_delta_pp=`-9.091`, exp_delta=`562.727`, mean_time_overhead_ratio=`3.235898`
- `narrow_passage` / `CX20-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-112.846`, mean_time_overhead_ratio=`3.735689`
- `parasol_misc` / `CX20-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-13.750`, mean_time_overhead_ratio=`5.889965`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`

## Final Readout
- result: public ceiling gate cleared.