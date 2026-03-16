# CX26-C Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; this round intentionally stayed public-first and did not consume hard-test evidence
- chosen params: `{'min_hits': 3, 'support_slack': 0.22, 'tail_thr': 0.55, 'max_macros': 3}`
- output root: `outputs/rs_p0cx26_c_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`-14.286`
- exp_delta=`1218.571`
- mean_time_overhead_ratio=`2.656792`

## Calib Family Breakdown
- `flange`: exp_delta=`7682.000`, mean_time_overhead_ratio=`0.247743`
- `maze`: exp_delta=`65.667`, mean_time_overhead_ratio=`3.274870`
- `narrow_passage`: exp_delta=`381.000`, mean_time_overhead_ratio=`2.297619`
- `parasol_misc`: exp_delta=`-111.000`, mean_time_overhead_ratio=`3.929949`

## Public Parasol vs `CX3-D`
- `exp4` / `CX26-C (Full)`: success_delta_pp=`0.000`, exp_delta=`392.889`, mean_time_overhead_ratio=`2.776835`
- `exp4` / `CX26-C (No-TDC)`: success_delta_pp=`0.000`, exp_delta=`392.889`, mean_time_overhead_ratio=`2.769672`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.028351`

## Public `exp4` Family Breakdown
- `alpha_puzzle` / `CX26-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`4.155300`
- `alpha_puzzle` / `CX26-C (No-TDC)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`4.741610`
- `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.050884`
- `bug_trap` / `CX26-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`3.188268`
- `bug_trap` / `CX26-C (No-TDC)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`3.159198`
- `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.219008`
- `flange` / `CX26-C (Full)`: success_delta_pp=`0.000`, exp_delta=`1428.400`, mean_time_overhead_ratio=`2.602923`
- `flange` / `CX26-C (No-TDC)`: success_delta_pp=`0.000`, exp_delta=`1428.400`, mean_time_overhead_ratio=`2.595096`
- `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`42.600`, mean_time_overhead_ratio=`-0.002614`
- `maze` / `CX26-C (Full)`: success_delta_pp=`0.000`, exp_delta=`-113.000`, mean_time_overhead_ratio=`6.575107`
- `maze` / `CX26-C (No-TDC)`: success_delta_pp=`0.000`, exp_delta=`-113.000`, mean_time_overhead_ratio=`6.574614`
- `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.030750`
- `narrow_passage` / `CX26-C (Full)`: success_delta_pp=`0.000`, exp_delta=`98.250`, mean_time_overhead_ratio=`2.986559`
- `narrow_passage` / `CX26-C (No-TDC)`: success_delta_pp=`0.000`, exp_delta=`98.250`, mean_time_overhead_ratio=`2.981555`
- `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.006491`
- `parasol_misc` / `CX26-C (Full)`: success_delta_pp=`0.000`, exp_delta=`-58.333`, mean_time_overhead_ratio=`3.907812`
- `parasol_misc` / `CX26-C (No-TDC)`: success_delta_pp=`0.000`, exp_delta=`-58.333`, mean_time_overhead_ratio=`3.889259`
- `parasol_misc` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-451.500`, mean_time_overhead_ratio=`0.950310`

## Hard Benchmark vs `CX3-D`
- skipped: this round intentionally stayed public-first / ordinary-support; no hard-test evidence was consumed.

## Hard Family Breakdown
- skipped: this round intentionally stayed public-first / ordinary-support; no hard-test evidence was consumed.

## DTO Contract
- contract saved to `outputs/rs_p0cx26_c_pilot_v1/dto_contract.json`

## Observatory
- diagnostic rows saved to `outputs/rs_p0cx26_c_pilot_v1/diagnostic_rows.csv`; state_counts=`{'candidate': 20497, 'commit': 36315, 'recover': 17498, 'observe': 9050}`

## Failure Diagnosis
- `outputs/rs_p0cx26_c_pilot_v1/trials/trial_01/tdc_meta.json` reports `has_tail_band=false`, so no structural tail support band was compiled from `calib_hard_v1/train`.
- Public `diagnostic_rows.csv` still shows `occupancy_hotspot_score=0`, `transition_hotspot_score=0`, `false_commit_ledger_hit=0` for all traced states, so there is no upstream DTO evidence for tail-only downgrade either.
- Consequence: `RS-TDC` never activates; `CX26-C (Full)` is expansion-identical to `CX26-C (No-TDC)` and `CX23-C (Full)`, with only additional DTO bookkeeping overhead left behind.

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
