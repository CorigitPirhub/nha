# CX26-B Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; this round intentionally stayed public-first and did not consume hard-test evidence
- chosen params: `{'occ_thr': 0.3, 'trans_thr': 0.3, 'dynamic_thr': 0.4, 'support_slack': 0.18, 'budget_review': 16, 'budget_intervene': 8, 'margin_scale': 0.6, 'max_macros': 3}`
- output root: `outputs/rs_p0cx26_b_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`-14.286`
- exp_delta=`1218.571`
- mean_time_overhead_ratio=`2.653697`

## Calib Family Breakdown
- `flange`: exp_delta=`7682.000`, mean_time_overhead_ratio=`0.252053`
- `maze`: exp_delta=`65.667`, mean_time_overhead_ratio=`3.272208`
- `narrow_passage`: exp_delta=`381.000`, mean_time_overhead_ratio=`2.291758`
- `parasol_misc`: exp_delta=`-111.000`, mean_time_overhead_ratio=`3.923683`

## Public Parasol vs `CX3-D`
- `exp4` / `CX26-B (Full)`: success_delta_pp=`0.000`, exp_delta=`392.889`, mean_time_overhead_ratio=`2.776023`
- `exp4` / `CX26-B (No-MGI)`: success_delta_pp=`0.000`, exp_delta=`392.889`, mean_time_overhead_ratio=`2.774499`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.028351`

## Public `exp4` Family Breakdown
- `alpha_puzzle` / `CX26-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`4.080240`
- `alpha_puzzle` / `CX26-B (No-MGI)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`4.900188`
- `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.050884`
- `bug_trap` / `CX26-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`3.188783`
- `bug_trap` / `CX26-B (No-MGI)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`3.192895`
- `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.219008`
- `flange` / `CX26-B (Full)`: success_delta_pp=`0.000`, exp_delta=`1428.400`, mean_time_overhead_ratio=`2.602337`
- `flange` / `CX26-B (No-MGI)`: success_delta_pp=`0.000`, exp_delta=`1428.400`, mean_time_overhead_ratio=`2.598741`
- `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`42.600`, mean_time_overhead_ratio=`-0.002614`
- `maze` / `CX26-B (Full)`: success_delta_pp=`0.000`, exp_delta=`-113.000`, mean_time_overhead_ratio=`6.587849`
- `maze` / `CX26-B (No-MGI)`: success_delta_pp=`0.000`, exp_delta=`-113.000`, mean_time_overhead_ratio=`6.643435`
- `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.030750`
- `narrow_passage` / `CX26-B (Full)`: success_delta_pp=`0.000`, exp_delta=`98.250`, mean_time_overhead_ratio=`2.984828`
- `narrow_passage` / `CX26-B (No-MGI)`: success_delta_pp=`0.000`, exp_delta=`98.250`, mean_time_overhead_ratio=`2.987522`
- `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.006491`
- `parasol_misc` / `CX26-B (Full)`: success_delta_pp=`0.000`, exp_delta=`-58.333`, mean_time_overhead_ratio=`3.911126`
- `parasol_misc` / `CX26-B (No-MGI)`: success_delta_pp=`0.000`, exp_delta=`-58.333`, mean_time_overhead_ratio=`3.901654`
- `parasol_misc` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-451.500`, mean_time_overhead_ratio=`0.950310`

## Hard Benchmark vs `CX3-D`
- skipped: this round intentionally stayed public-first / ordinary-support; no hard-test evidence was consumed.

## Hard Family Breakdown
- skipped: this round intentionally stayed public-first / ordinary-support; no hard-test evidence was consumed.

## DTO Contract
- contract saved to `outputs/rs_p0cx26_b_pilot_v1/dto_contract.json`

## Observatory
- diagnostic rows saved to `outputs/rs_p0cx26_b_pilot_v1/diagnostic_rows.csv`; state_counts=`{'candidate': 20497, 'commit': 36315, 'recover': 17498, 'observe': 9050}`

## Failure Diagnosis
- `outputs/rs_p0cx26_b_pilot_v1/trials/trial_01/mgi_meta.json` only yields a weak calibration object: `pass_margin=-0.0383`, `reject_margin=0.0`.
- Public `diagnostic_rows.csv` again shows `occupancy_hotspot_score=0`, `transition_hotspot_score=0`, `false_commit_ledger_hit=0` across all traced states, and no `mgi_z` field is ever emitted.
- Consequence: monotone graded intervention never activates; `CX26-B (Full)` is expansion-identical to `CX26-B (No-MGI)` and to `CX23-C (Full)`, with the runtime penalty coming from DTO evidence construction rather than changed search behavior.

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
