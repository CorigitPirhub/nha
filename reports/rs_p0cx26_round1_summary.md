# P0-CX26 Round1 Summary

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; this round stayed public-first and did not consume hard-test evidence

## Variant Readout
- `CX26-A`: calib_val exp_delta=`1218.571`, calib_val overhead=`2.633065`, exp4 exp_delta=`392.889`, exp4 overhead=`2.751741`, flange exp_delta=`1428.400`
- `CX26-B`: calib_val exp_delta=`1218.571`, calib_val overhead=`2.653697`, exp4 exp_delta=`392.889`, exp4 overhead=`2.776023`, flange exp_delta=`1428.400`
- `CX26-C`: calib_val exp_delta=`1218.571`, calib_val overhead=`2.656792`, exp4 exp_delta=`392.889`, exp4 overhead=`2.776835`, flange exp_delta=`1428.400`

## Cross-Variant Diagnosis
- `outputs/rs_p0cx26_[a|b|c]_pilot_v1/public_case_rows.csv` shows all three `CX26-* (Full)` branches are expansion-identical to `CX23-C (Full)` on every `exp4` case; the public signal is inherited, not new.
- `CX26-A`: `HST` never fires because the compiled false ledgers are empty and the hotspot channels stay at zero on all public diagnostic rows.
- `CX26-B`: `MGI` never emits an intervention scalar; calibration collapses to a weak boundary and the DTO hotspot channels stay at zero.
- `CX26-C`: `TDC` never compiles a usable tail band (`has_tail_band=false`), so no tail-only downgrade path exists.
- Shared root cause: the current DTO evidence surface collapses to non-discriminative constants (`occupancy/transition/ledger=0`, `local_proxy_disagreement=0.5`, `tail_uncertainty=1.0`), so the new control layers add runtime but do not change search decisions.

## Ordering
- rank 1: `CX26-A`
- rank 2: `CX26-B`
- rank 3: `CX26-C`

## Verdict
- No `CX26` branch is promotable. Public `exp4` remains at the old `CX23-C` ceiling (`+392.889`) with the same family pattern (`flange=+1428.4`, `narrow_passage=+98.25`, `maze=-113.0`, `parasol_misc=-58.333`) but much worse overhead (`~2.75x` vs `CX23-C`).
- `mp/csm` ordinary-support remains clean: all audited `CX26-A/B/C` wrappers keep `max_abs_field_diff=0.0`.
- If this line is continued, the next repair target is not another trigger/intervention variant; it is the DTO compiler itself, which currently fails to produce usable hotspot, ledger, or tail-support evidence.
