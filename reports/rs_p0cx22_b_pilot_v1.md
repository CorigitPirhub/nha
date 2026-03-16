# CX22-B Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; hard-test consumed only when the frozen public gate passes
- chosen params: `{'activation_thr': 0.18, 'hard_conf_thr': 0.5, 'risk_score_thr': 0.0, 'min_future_gain': 0.1}`
- output root: `outputs/rs_p0cx22_b_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`0.000`
- exp_delta=`0.000`
- mean_time_overhead_ratio=`0.694672`

## Calib Family Breakdown
- `flange`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.766199`
- `maze`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.664163`
- `narrow_passage`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.689666`
- `parasol_misc`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.724684`

## Public Parasol vs `CX3-D`
- `exp4` / `CX22-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.701371`
- `exp4` / `CX22-B (No-Conformal)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.698259`
- `exp4` / `CX22-B (No-Decision-Gate)`: success_delta_pp=`0.000`, exp_delta=`336.667`, mean_time_overhead_ratio=`3.253864`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.028351`

## Public `exp4` Family Breakdown
- `alpha_puzzle` / `CX22-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.738174`
- `alpha_puzzle` / `CX22-B (No-Conformal)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.729092`
- `alpha_puzzle` / `CX22-B (No-Decision-Gate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`3.620282`
- `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.050884`
- `bug_trap` / `CX22-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.677626`
- `bug_trap` / `CX22-B (No-Conformal)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.673447`
- `bug_trap` / `CX22-B (No-Decision-Gate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`3.475224`
- `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.219008`
- `flange` / `CX22-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.700657`
- `flange` / `CX22-B (No-Conformal)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.699743`
- `flange` / `CX22-B (No-Decision-Gate)`: success_delta_pp=`0.000`, exp_delta=`1485.400`, mean_time_overhead_ratio=`2.961191`
- `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`42.600`, mean_time_overhead_ratio=`-0.002614`
- `maze` / `CX22-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.712864`
- `maze` / `CX22-B (No-Conformal)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.714267`
- `maze` / `CX22-B (No-Decision-Gate)`: success_delta_pp=`0.000`, exp_delta=`-117.000`, mean_time_overhead_ratio=`7.221479`
- `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.030750`
- `narrow_passage` / `CX22-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.699505`
- `narrow_passage` / `CX22-B (No-Conformal)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.692570`
- `narrow_passage` / `CX22-B (No-Decision-Gate)`: success_delta_pp=`0.000`, exp_delta=`-99.500`, mean_time_overhead_ratio=`3.633164`
- `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.006491`
- `parasol_misc` / `CX22-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.731823`
- `parasol_misc` / `CX22-B (No-Conformal)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.722720`
- `parasol_misc` / `CX22-B (No-Decision-Gate)`: success_delta_pp=`0.000`, exp_delta=`-142.000`, mean_time_overhead_ratio=`5.044005`
- `parasol_misc` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-451.500`, mean_time_overhead_ratio=`0.950310`

## Hard Benchmark vs `CX3-D`
- skipped: this round keeps hard-test for `CX22-C/D` only; `CX22-A/B` stay public-first.

## Hard Family Breakdown
- skipped: this round keeps hard-test for `CX22-C/D` only; `CX22-A/B` stay public-first.

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`