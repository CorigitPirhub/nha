# P0-CX24 Round1 Summary

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; this round stayed public-first and did not consume hard-test evidence

## Variant Readout
- `CX24-E`: calib_val exp_delta=`1218.571`, calib_val overhead=`1.330486`, exp4 exp_delta=`392.889`, exp4 overhead=`1.390389`, flange exp_delta=`1428.400`
- `CX24-A`: calib_val exp_delta=`1218.571`, calib_val overhead=`1.442802`, exp4 exp_delta=`392.889`, exp4 overhead=`1.528259`, flange exp_delta=`1428.400`
- `CX24-D`: calib_val exp_delta=`34.571`, calib_val overhead=`1.962058`, exp4 exp_delta=`61.444`, exp4 overhead=`1.728946`, flange exp_delta=`218.000`
- `CX24-B`: calib_val exp_delta=`1218.571`, calib_val overhead=`1.375541`, exp4 exp_delta=`392.889`, exp4 overhead=`1.447765`, flange exp_delta=`1428.400`
- `CX24-C`: calib_val exp_delta=`1218.571`, calib_val overhead=`1.352961`, exp4 exp_delta=`392.889`, exp4 overhead=`1.418766`, flange exp_delta=`1428.400`

## Ordering
- rank 1: `CX24-C`
- rank 2: `CX24-E`
- rank 3: `CX24-B`
- rank 4: `CX24-A`
- rank 5: `CX24-D`

## Readout
- `CX24-E` succeeds as instrumentation only: it keeps `CX23-C`-level public gains while emitting automaton diagnostics, including state occupancy and trace rows, but it does not itself improve the policy.
- `CX24-A` shows the current maze trap witness is ineffective: public metrics are essentially unchanged from `CX24-E`, and `No-Trap-Witness` is slightly cheaper, so the witness object has not yet learned a useful suppressor.
- `CX24-D` is the only branch that materially changes behavior: the counterfactual commit certificate repairs `maze` from `-113.0` to `0.0` and lifts `narrow_passage` to `+104.5`, but it does so by collapsing most of the `flange` leverage from `+1428.4` to `+218.0`, leaving only `+61.444` overall.
- `CX24-B` and `CX24-C` do not move the needle beyond `CX23-C`: tail-aware abstention and group-robust gating, as currently implemented, leave the family pattern essentially unchanged.
- no `CX24` branch is promotable; accepted mainline remains `RS + refined CX3-D / RS-HPG`.
