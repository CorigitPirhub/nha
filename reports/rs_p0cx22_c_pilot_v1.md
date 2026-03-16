# CX22-C Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; hard-test consumed only when the frozen public gate passes
- chosen params: `{'max_depth': 3, 'prob_thr': 0.7, 'min_exp_delta': 50.0}`
- output root: `outputs/rs_p0cx22_c_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`0.000`
- exp_delta=`0.000`
- mean_time_overhead_ratio=`0.013149`

## Calib Family Breakdown
- `flange`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.036211`
- `maze`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.002973`
- `narrow_passage`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.015105`
- `parasol_misc`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.016703`

## Public Parasol vs `CX3-D`
- `exp4` / `CX22-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.000388`
- `exp4` / `CX22-C (No-Episode-Gate)`: success_delta_pp=`0.000`, exp_delta=`351.722`, mean_time_overhead_ratio=`3.220611`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.028351`

## Public `exp4` Family Breakdown
- `alpha_puzzle` / `CX22-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.058856`
- `alpha_puzzle` / `CX22-C (No-Episode-Gate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`3.607139`
- `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.050884`
- `bug_trap` / `CX22-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.114988`
- `bug_trap` / `CX22-C (No-Episode-Gate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`3.556429`
- `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.219008`
- `flange` / `CX22-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.000337`
- `flange` / `CX22-C (No-Episode-Gate)`: success_delta_pp=`0.000`, exp_delta=`1482.600`, mean_time_overhead_ratio=`2.940653`
- `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`42.600`, mean_time_overhead_ratio=`-0.002614`
- `maze` / `CX22-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.002726`
- `maze` / `CX22-C (No-Episode-Gate)`: success_delta_pp=`0.000`, exp_delta=`-117.000`, mean_time_overhead_ratio=`7.187817`
- `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.030750`
- `narrow_passage` / `CX22-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.001382`
- `narrow_passage` / `CX22-C (No-Episode-Gate)`: success_delta_pp=`0.000`, exp_delta=`-99.750`, mean_time_overhead_ratio=`3.614617`
- `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.006491`
- `parasol_misc` / `CX22-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.030170`
- `parasol_misc` / `CX22-C (No-Episode-Gate)`: success_delta_pp=`0.000`, exp_delta=`-94.333`, mean_time_overhead_ratio=`4.629709`
- `parasol_misc` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-451.500`, mean_time_overhead_ratio=`0.950310`

## Hard Benchmark vs `CX3-D`
- skipped: frozen public gate did not clear, so hard-test evidence was not consumed.

## Hard Family Breakdown
- skipped: frozen public gate did not clear, so hard-test evidence was not consumed.

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`