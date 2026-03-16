# CX26-A Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; this round intentionally stayed public-first and did not consume hard-test evidence
- chosen params: `{'occ_thr': 0.35, 'trans_thr': 0.35, 'dynamic_thr': 0.45, 'churn_thr': 0.18, 'loop_thr': 0.06, 'disagreement_thr': 0.45, 'budget_review': 16, 'budget_intervene': 8, 'commit_margin': 0.04, 'sibling_margin': 0.02, 'max_macros': 3}`
- output root: `outputs/rs_p0cx26_a_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`-14.286`
- exp_delta=`1218.571`
- mean_time_overhead_ratio=`2.633065`

## Calib Family Breakdown
- `flange`: exp_delta=`7682.000`, mean_time_overhead_ratio=`0.246503`
- `maze`: exp_delta=`65.667`, mean_time_overhead_ratio=`3.252662`
- `narrow_passage`: exp_delta=`381.000`, mean_time_overhead_ratio=`2.269300`
- `parasol_misc`: exp_delta=`-111.000`, mean_time_overhead_ratio=`3.888364`

## Public Parasol vs `CX3-D`
- `exp4` / `CX26-A (Full)`: success_delta_pp=`0.000`, exp_delta=`392.889`, mean_time_overhead_ratio=`2.751741`
- `exp4` / `CX26-A (No-Hotspot-Trigger)`: success_delta_pp=`0.000`, exp_delta=`392.889`, mean_time_overhead_ratio=`2.746822`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.028351`

## Public `exp4` Family Breakdown
- `alpha_puzzle` / `CX26-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`4.163151`
- `alpha_puzzle` / `CX26-A (No-Hotspot-Trigger)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`5.113766`
- `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.050884`
- `bug_trap` / `CX26-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`3.159147`
- `bug_trap` / `CX26-A (No-Hotspot-Trigger)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`3.175133`
- `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.219008`
- `flange` / `CX26-A (Full)`: success_delta_pp=`0.000`, exp_delta=`1428.400`, mean_time_overhead_ratio=`2.581140`
- `flange` / `CX26-A (No-Hotspot-Trigger)`: success_delta_pp=`0.000`, exp_delta=`1428.400`, mean_time_overhead_ratio=`2.573570`
- `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`42.600`, mean_time_overhead_ratio=`-0.002614`
- `maze` / `CX26-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-113.000`, mean_time_overhead_ratio=`6.528026`
- `maze` / `CX26-A (No-Hotspot-Trigger)`: success_delta_pp=`0.000`, exp_delta=`-113.000`, mean_time_overhead_ratio=`6.592251`
- `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.030750`
- `narrow_passage` / `CX26-A (Full)`: success_delta_pp=`0.000`, exp_delta=`98.250`, mean_time_overhead_ratio=`2.955649`
- `narrow_passage` / `CX26-A (No-Hotspot-Trigger)`: success_delta_pp=`0.000`, exp_delta=`98.250`, mean_time_overhead_ratio=`2.955910`
- `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.006491`
- `parasol_misc` / `CX26-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-58.333`, mean_time_overhead_ratio=`3.875475`
- `parasol_misc` / `CX26-A (No-Hotspot-Trigger)`: success_delta_pp=`0.000`, exp_delta=`-58.333`, mean_time_overhead_ratio=`3.863168`
- `parasol_misc` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-451.500`, mean_time_overhead_ratio=`0.950310`

## Hard Benchmark vs `CX3-D`
- skipped: this round intentionally stayed public-first / ordinary-support; no hard-test evidence was consumed.

## Hard Family Breakdown
- skipped: this round intentionally stayed public-first / ordinary-support; no hard-test evidence was consumed.

## DTO Contract
- contract saved to `outputs/rs_p0cx26_a_pilot_v1/dto_contract.json`

## Observatory
- diagnostic rows saved to `outputs/rs_p0cx26_a_pilot_v1/diagnostic_rows.csv`; state_counts=`{'candidate': 20497, 'commit': 36315, 'recover': 17498, 'observe': 9050}`

## Failure Diagnosis
- `outputs/rs_p0cx26_a_pilot_v1/trials/trial_01/hst_meta.json` shows `false_classes=[]` and `false_transitions=[]`, so the compiled hotspot ledger is empty.
- Public `diagnostic_rows.csv` shows `occupancy_hotspot_score=0`, `transition_hotspot_score=0`, `false_commit_ledger_hit=0` for all traced states, while `dto_review_budget_left` / `dto_intervene_budget_left` never decrease from their initial values.
- Consequence: `RS-HST` never actually fires; `CX26-A (Full)` is expansion-identical to both `CX26-A (No-Hotspot-Trigger)` and `CX23-C (Full)`, and the only observable effect is extra DTO bookkeeping overhead.

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
