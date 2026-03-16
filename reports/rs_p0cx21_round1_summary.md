# P0-CX21 Round1 Summary

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow` `exp4` evaluation + `mp/csm` ordinary-support audit; this first implementation round intentionally stayed public-first and did not consume hard-test evidence

## Variant Readout
- `CX21-A`: calib_val exp_delta=`-833.143`, calib_val overhead=`5.338310`, exp4 exp_delta=`55.611`, exp4 overhead=`4.936051`, flange exp_delta=`173.800`, hard_escalated=`0`
- `CX21-B`: calib_val exp_delta=`350.143`, calib_val overhead=`3.379024`, exp4 exp_delta=`351.722`, exp4 overhead=`3.347043`, flange exp_delta=`1482.600`, hard_escalated=`0`
- `CX21-C`: calib_val exp_delta=`-723.857`, calib_val overhead=`4.115335`, exp4 exp_delta=`56.611`, exp4 overhead=`3.748104`, flange exp_delta=`303.600`, hard_escalated=`0`

## Ordering
- rank 1: `CX21-B`
- rank 2: `CX21-C`
- rank 3: `CX21-A`

## Readout
- `CX21-B` regains the strongest public ceiling in this round, but the gain is concentrated in `flange` and comes with `3.347043` mean time overhead plus negative `maze / narrow_passage / parasol_misc`.
- `CX21-A` and `CX21-C` retain only small public gains, and `CX21-C` shows no observable contribution beyond its `No-Stable-Graph` ablation.
- no `CX21` branch is promotable; accepted mainline remains `RS + refined CX3-D / RS-HPG`.
