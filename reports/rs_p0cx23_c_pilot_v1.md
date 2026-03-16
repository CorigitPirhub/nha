# CX23-C Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; this round intentionally stayed public-first and did not consume hard-test evidence
- chosen params: `{'min_hits': 4, 'min_gain': 0.05, 'commit_steps': 3, 'recover_steps': 4, 'max_macros': 3}`
- output root: `outputs/rs_p0cx23_c_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`-14.286`
- exp_delta=`1218.571`
- mean_time_overhead_ratio=`1.297095`

## Calib Family Breakdown
- `flange`: exp_delta=`7682.000`, mean_time_overhead_ratio=`-0.213969`
- `maze`: exp_delta=`65.667`, mean_time_overhead_ratio=`1.697965`
- `narrow_passage`: exp_delta=`381.000`, mean_time_overhead_ratio=`1.064300`
- `parasol_misc`: exp_delta=`-111.000`, mean_time_overhead_ratio=`2.071138`

## Public Parasol vs `CX3-D`
- `exp4` / `CX23-C (Full)`: success_delta_pp=`0.000`, exp_delta=`392.889`, mean_time_overhead_ratio=`1.359640`
- `exp4` / `CX23-C (No-Automaton)`: success_delta_pp=`0.000`, exp_delta=`326.333`, mean_time_overhead_ratio=`1.543508`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.028351`

## Public `exp4` Family Breakdown
- `alpha_puzzle` / `CX23-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.664658`
- `alpha_puzzle` / `CX23-C (No-Automaton)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.653020`
- `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.050884`
- `bug_trap` / `CX23-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.547206`
- `bug_trap` / `CX23-C (No-Automaton)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.607261`
- `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.219008`
- `flange` / `CX23-C (Full)`: success_delta_pp=`0.000`, exp_delta=`1428.400`, mean_time_overhead_ratio=`1.251352`
- `flange` / `CX23-C (No-Automaton)`: success_delta_pp=`0.000`, exp_delta=`1424.000`, mean_time_overhead_ratio=`1.366817`
- `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`42.600`, mean_time_overhead_ratio=`-0.002614`
- `maze` / `CX23-C (Full)`: success_delta_pp=`0.000`, exp_delta=`-113.000`, mean_time_overhead_ratio=`3.729734`
- `maze` / `CX23-C (No-Automaton)`: success_delta_pp=`0.000`, exp_delta=`-113.000`, mean_time_overhead_ratio=`3.687448`
- `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.030750`
- `narrow_passage` / `CX23-C (Full)`: success_delta_pp=`0.000`, exp_delta=`98.250`, mean_time_overhead_ratio=`1.488878`
- `narrow_passage` / `CX23-C (No-Automaton)`: success_delta_pp=`0.000`, exp_delta=`-87.750`, mean_time_overhead_ratio=`1.785446`
- `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.006491`
- `parasol_misc` / `CX23-C (Full)`: success_delta_pp=`0.000`, exp_delta=`-58.333`, mean_time_overhead_ratio=`2.079646`
- `parasol_misc` / `CX23-C (No-Automaton)`: success_delta_pp=`0.000`, exp_delta=`-130.333`, mean_time_overhead_ratio=`2.515728`
- `parasol_misc` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-451.500`, mean_time_overhead_ratio=`0.950310`

## Hard Benchmark vs `CX3-D`
- skipped: this round intentionally stayed public-first / ordinary-support; no hard-test evidence was consumed.

## Hard Family Breakdown
- skipped: this round intentionally stayed public-first / ordinary-support; no hard-test evidence was consumed.

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`