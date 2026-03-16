# P0-CX9 Round-1 Summary

Status: `dev-only-pilot + CX9-A tuned pass`
Date: `2026-03-09`

Scope:
- split: `data/split/calib_hard_v1`
- protocol: dev-only pilot, no test data used
- comparator: accepted `RS + refined CX3-D / RS-HPG`

## Variant Results

### CX9-A / RS-SBM
- initial report: `reports/rs_p0cx9_a_pilot_v1.md`
- tuned report: `reports/rs_p0cx9_a_tuned_pilot_v1.md`
- tuned overall `success_delta_pp = 0.0`
- tuned overall `exp_delta = +814.714`
- tuned overall `mean_time_overhead_ratio = -0.0019`
- tuned reading: the only `CX9` branch that now satisfies both the relaxed efficiency gate and the positive-effect gate; `parasol_misc` is no longer negative.

### CX9-D / RS-BWR
- report: `reports/rs_p0cx9_d_pilot_v1.md`
- overall `success_delta_pp = 0.0`
- overall `exp_delta = -2.143`
- overall `mean_time_overhead_ratio = 0.3381`
- reading: sparse bottleneck-window review is computationally cheaper than `CX8-D`, but the semantic signal is too weak to produce a positive overall gain.

### CX9-B / RS-CSP
- report: `reports/rs_p0cx9_b_pilot_v1.md`
- overall `success_delta_pp = 0.0`
- overall `exp_delta = -602.429`
- overall `mean_time_overhead_ratio = 0.4930`
- reading: one-shot gate program currently harms both search effort and runtime.

### CX9-C / RS-CPF
- report: `reports/rs_p0cx9_c_pilot_v1.md`
- overall `success_delta_pp = 0.0`
- overall `exp_delta = 0.0`
- overall `mean_time_overhead_ratio = 0.8335`
- reading: dense conditional policy field collapses to parity in effect while remaining too expensive to precompute online.

## Ranking
1. `CX9-A / RS-SBM` (passed to next stage)
2. `CX9-D / RS-BWR`
3. `CX9-C / RS-CPF`
4. `CX9-B / RS-CSP`

## Current Verdict
- `CX9-A / RS-SBM` now satisfies the current relaxed gates on `calib_hard_v1` dev-only pilot:
  - `exp_delta > 0`
  - `success_delta_pp >= 0`
  - `mean_time_overhead_ratio < 0.30`
  - `parasol_misc exp_delta >= 0`
- Therefore `CX9-A` is promoted to the next evaluation stage.
- `CX9-D/B/C` remain non-promoted follow-up branches or frozen negatives.


## Postscript
- After this round-1 summary, `CX9-A / RS-SBM` underwent a tuned `Efficiency & Stability Sprint`; see `reports/rs_p0cx9_a_tuned_pilot_v1.md`.
- Under the relaxed current gate (`mean_time_overhead_ratio < 0.30`), the tuned `CX9-A` branch now passes the dev gate and is promoted to the next stage.
