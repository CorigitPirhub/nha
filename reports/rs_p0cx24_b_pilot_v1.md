# CX24-B Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; this round intentionally stayed public-first and did not consume hard-test evidence
- chosen params: `{'min_hits': 3, 'tail_thr': 0.15, 'support_slack': 0.22, 'max_macros': 3}`
- output root: `outputs/rs_p0cx24_b_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`-14.286`
- exp_delta=`1218.571`
- mean_time_overhead_ratio=`1.375541`

## Calib Family Breakdown
- `flange`: exp_delta=`7682.000`, mean_time_overhead_ratio=`-0.187890`
- `maze`: exp_delta=`65.667`, mean_time_overhead_ratio=`1.786891`
- `narrow_passage`: exp_delta=`381.000`, mean_time_overhead_ratio=`1.155917`
- `parasol_misc`: exp_delta=`-111.000`, mean_time_overhead_ratio=`2.144173`

## Public Parasol vs `CX3-D`
- `exp4` / `CX24-B (Full)`: success_delta_pp=`0.000`, exp_delta=`392.889`, mean_time_overhead_ratio=`1.447765`
- `exp4` / `CX24-B (No-Tail-Shield)`: success_delta_pp=`0.000`, exp_delta=`392.889`, mean_time_overhead_ratio=`1.402106`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.028351`

## Public `exp4` Family Breakdown
- `alpha_puzzle` / `CX24-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`2.184365`
- `alpha_puzzle` / `CX24-B (No-Tail-Shield)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`2.243612`
- `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.050884`
- `bug_trap` / `CX24-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.723018`
- `bug_trap` / `CX24-B (No-Tail-Shield)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.614923`
- `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.219008`
- `flange` / `CX24-B (Full)`: success_delta_pp=`0.000`, exp_delta=`1428.400`, mean_time_overhead_ratio=`1.331988`
- `flange` / `CX24-B (No-Tail-Shield)`: success_delta_pp=`0.000`, exp_delta=`1428.400`, mean_time_overhead_ratio=`1.291380`
- `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`42.600`, mean_time_overhead_ratio=`-0.002614`
- `maze` / `CX24-B (Full)`: success_delta_pp=`0.000`, exp_delta=`-113.000`, mean_time_overhead_ratio=`3.981070`
- `maze` / `CX24-B (No-Tail-Shield)`: success_delta_pp=`0.000`, exp_delta=`-113.000`, mean_time_overhead_ratio=`3.801732`
- `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.030750`
- `narrow_passage` / `CX24-B (Full)`: success_delta_pp=`0.000`, exp_delta=`98.250`, mean_time_overhead_ratio=`1.587838`
- `narrow_passage` / `CX24-B (No-Tail-Shield)`: success_delta_pp=`0.000`, exp_delta=`98.250`, mean_time_overhead_ratio=`1.534038`
- `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.006491`
- `parasol_misc` / `CX24-B (Full)`: success_delta_pp=`0.000`, exp_delta=`-58.333`, mean_time_overhead_ratio=`2.197167`
- `parasol_misc` / `CX24-B (No-Tail-Shield)`: success_delta_pp=`0.000`, exp_delta=`-58.333`, mean_time_overhead_ratio=`2.138504`
- `parasol_misc` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-451.500`, mean_time_overhead_ratio=`0.950310`

## Hard Benchmark vs `CX3-D`
- skipped: this round intentionally stayed public-first / ordinary-support; no hard-test evidence was consumed.

## Hard Family Breakdown
- skipped: this round intentionally stayed public-first / ordinary-support; no hard-test evidence was consumed.

## Observatory
- diagnostic rows saved to `outputs/rs_p0cx24_b_pilot_v1/diagnostic_rows.csv`; state_counts=`{'candidate': 20497, 'commit': 36315, 'recover': 17498, 'observe': 9050}`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`