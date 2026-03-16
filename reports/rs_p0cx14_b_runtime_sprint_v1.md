# P0-CX14-B Runtime Sprint V1

- protocol: dev-only selection on `calib_hard_v1`, then locked public `parasol_narrow` evaluation; `rs_root_hard_v2/test` is consumed only if the public gate clears
- chosen params: `{'base_penalty': 0.04, 'update_gain': 0.14, 'activation_progress_threshold': 0.01, 'stall_threshold': 0.018, 'accept_ratio_threshold': 0.25, 'trap_weight': 0.04, 'corridor_bonus': 0.012, 'repeat_trigger': 1, 'global_stall_trigger': 2, 'stride_cells': 2, 'yaw_stride': 2, 'progress_depth': 1, 'max_penalty': 0.28}`
- output root: `outputs/rs_p0cx14_b_runtime_sprint_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`0.000`
- exp_delta=`0.000`
- mean_time_overhead_ratio=`0.286833`

## Calib Family Breakdown
- `flange`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.310340`
- `maze`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.295916`
- `narrow_passage`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.256450`
- `parasol_misc`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.296843`

## Public Parasol vs `CX3-D`
- `exp3` / `CX14-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.281385`
- `exp3` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-130.333`, mean_time_overhead_ratio=`0.042909`
- `exp4` / `CX14-B (Always-Active)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.279432`
- `exp4` / `CX14-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.282318`
- `exp4` / `CX14-B (No-Update)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.270544`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.028351`

## Public `exp4` Family Breakdown
- `alpha_puzzle` / `CX14-B (Always-Active)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.278444`
- `alpha_puzzle` / `CX14-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.241923`
- `alpha_puzzle` / `CX14-B (No-Update)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.210056`
- `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.050884`
- `bug_trap` / `CX14-B (Always-Active)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.219682`
- `bug_trap` / `CX14-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.211713`
- `bug_trap` / `CX14-B (No-Update)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.195452`
- `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.219008`
- `flange` / `CX14-B (Always-Active)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.279424`
- `flange` / `CX14-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.284191`
- `flange` / `CX14-B (No-Update)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.270830`
- `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`42.600`, mean_time_overhead_ratio=`-0.002614`
- `maze` / `CX14-B (Always-Active)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.259924`
- `maze` / `CX14-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.262528`
- `maze` / `CX14-B (No-Update)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.243640`
- `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.030750`
- `narrow_passage` / `CX14-B (Always-Active)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.278430`
- `narrow_passage` / `CX14-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.278222`
- `narrow_passage` / `CX14-B (No-Update)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.269755`
- `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.006491`
- `parasol_misc` / `CX14-B (Always-Active)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.290170`
- `parasol_misc` / `CX14-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.286699`
- `parasol_misc` / `CX14-B (No-Update)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.274423`
- `parasol_misc` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-451.500`, mean_time_overhead_ratio=`0.950310`

## Hard Benchmark vs `CX3-D`
- skipped: public gate did not clear, so hard-test evidence was not consumed.

## Hard Family Breakdown
- skipped: no hard-family rows because hard escalation was not triggered.

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`

## Final Readout
- result: runtime compression does not clear the public gate under the locked protocol, so hard-test escalation is skipped.
