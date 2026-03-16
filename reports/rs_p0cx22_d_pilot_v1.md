# CX22-D Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; this round stayed public-first and did not consume hard-test evidence
- chosen params: `{'min_hits': 4, 'lcb_q': 0.2, 'min_score': 0.0}`
- output root: `outputs/rs_p0cx22_d_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`-14.286`
- exp_delta=`471.571`
- mean_time_overhead_ratio=`2.598582`

## Calib Family Breakdown
- note: chosen branch selection is preserved in `outputs/rs_p0cx22_d_pilot_v1/chosen.json`; the val-side signal remains strongly flange-concentrated and overall negative on success, consistent with the candidate log.

## Public Parasol vs `CX3-D`
- `exp4` / `CX22-D (Full)`: success_delta_pp=`0.000`, exp_delta=`326.333`, mean_time_overhead_ratio=`2.647250`
- `exp4` / `CX22-D (No-Class-Gate)`: success_delta_pp=`0.000`, exp_delta=`351.722`, mean_time_overhead_ratio=`3.215779`
- `exp4` / `CX22-D (No-LCB)`: success_delta_pp=`0.000`, exp_delta=`326.333`, mean_time_overhead_ratio=`2.651743`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.028351`

## Public `exp4` Family Breakdown
- `alpha_puzzle` / `CX22-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`2.836880`
- `alpha_puzzle` / `CX22-D (No-Class-Gate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`3.565783`
- `alpha_puzzle` / `CX22-D (No-LCB)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`2.861091`
- `bug_trap` / `CX22-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`2.784209`
- `bug_trap` / `CX22-D (No-Class-Gate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`3.471473`
- `bug_trap` / `CX22-D (No-LCB)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`2.803526`
- `flange` / `CX22-D (Full)`: success_delta_pp=`0.000`, exp_delta=`1424.000`, mean_time_overhead_ratio=`2.396019`
- `flange` / `CX22-D (No-Class-Gate)`: success_delta_pp=`0.000`, exp_delta=`1482.600`, mean_time_overhead_ratio=`2.936268`
- `flange` / `CX22-D (No-LCB)`: success_delta_pp=`0.000`, exp_delta=`1424.000`, mean_time_overhead_ratio=`2.399387`
- `maze` / `CX22-D (Full)`: success_delta_pp=`0.000`, exp_delta=`-113.000`, mean_time_overhead_ratio=`5.731753`
- `maze` / `CX22-D (No-Class-Gate)`: success_delta_pp=`0.000`, exp_delta=`-117.000`, mean_time_overhead_ratio=`7.179419`
- `maze` / `CX22-D (No-LCB)`: success_delta_pp=`0.000`, exp_delta=`-113.000`, mean_time_overhead_ratio=`5.743984`
- `narrow_passage` / `CX22-D (Full)`: success_delta_pp=`0.000`, exp_delta=`-87.750`, mean_time_overhead_ratio=`2.988115`
- `narrow_passage` / `CX22-D (No-Class-Gate)`: success_delta_pp=`0.000`, exp_delta=`-99.750`, mean_time_overhead_ratio=`3.614608`
- `narrow_passage` / `CX22-D (No-LCB)`: success_delta_pp=`0.000`, exp_delta=`-87.750`, mean_time_overhead_ratio=`2.994482`
- `parasol_misc` / `CX22-D (Full)`: success_delta_pp=`0.000`, exp_delta=`-130.333`, mean_time_overhead_ratio=`4.057058`
- `parasol_misc` / `CX22-D (No-Class-Gate)`: success_delta_pp=`0.000`, exp_delta=`-94.333`, mean_time_overhead_ratio=`4.571469`
- `parasol_misc` / `CX22-D (No-LCB)`: success_delta_pp=`0.000`, exp_delta=`-130.333`, mean_time_overhead_ratio=`4.064764`

## Hard Benchmark vs `CX3-D`
- skipped: this implementation round stayed public-first / ordinary-support; no hard-test evidence was consumed.

## Hard Family Breakdown
- skipped: this implementation round stayed public-first / ordinary-support; no hard-test evidence was consumed.

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`

## Final Readout
- result: shadow adoption preserves most of the `flange` gain while trimming runtime versus `No-Class-Gate`, but it still leaves `maze / narrow_passage / parasol_misc` negative and remains far above deployment budget.
