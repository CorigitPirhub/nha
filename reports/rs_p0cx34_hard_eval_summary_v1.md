# P0-CX34 Hard Eval Summary V1

- protocol: frozen hard-test evaluation with canonical `CX34-A` params; no retuning after public acceptance
- report: `reports/rs_p0cx34_a_hard_eval_v1.md`

## Overall vs `CX3-D`
- `CX34-A (Mainline)`: success_delta_pp=`2.740`, exp_delta=`196.548`, mean_time_overhead_ratio=`2.592819`, path_delta=`-1.179`

## Reading
- hard-test overall is positive, so `CX34-A` no longer fails the overall hard generalization gate
- the remaining blockers are runtime overhead and the hard-family negatives on `deadend_labyrinth`, `flange`, and `parasol_misc`
