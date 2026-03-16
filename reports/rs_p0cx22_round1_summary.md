# P0-CX22 Round1 Summary

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; this round stayed public-first and did not consume hard-test evidence

## Variant Readout
- `CX22-A`: calib_val exp_delta=`309.429`, calib_val overhead=`3.448779`, exp4 exp_delta=`333.778`, exp4 overhead=`3.230091`, flange exp_delta=`1484.000`, hard_escalated=`0`
- `CX22-B`: calib_val exp_delta=`0.000`, calib_val overhead=`0.694672`, exp4 exp_delta=`0.000`, exp4 overhead=`0.701371`, flange exp_delta=`0.000`, hard_escalated=`0`
- `CX22-C`: calib_val exp_delta=`0.000`, calib_val overhead=`0.013149`, exp4 exp_delta=`0.000`, exp4 overhead=`0.000388`, flange exp_delta=`0.000`, hard_escalated=`0`
- `CX22-D`: calib_val exp_delta=`471.571`, calib_val overhead=`2.598582`, exp4 exp_delta=`326.333`, exp4 overhead=`2.647250`, flange exp_delta=`1424.000`, hard_escalated=`0`

## Ordering
- rank 1: `CX22-A`
- rank 2: `CX22-D`
- rank 3: `CX22-B`
- rank 4: `CX22-C`

## Readout
- `CX22-A` compresses `CX21-B` only weakly: runtime remains `3.230x`, `flange` stays very strong, but `maze / narrow_passage / parasol_misc` remain negative and `No-Tree` is actually stronger overall.
- `CX22-B` proves the decision-point/conformal gate can almost fully suppress runtime and family damage, but it does so by collapsing the entire legality gain to public tie.
- `CX22-C` pushes that logic further: episode-level promotion gate nearly reduces the branch to baseline-equivalent behavior; the `No-Episode-Gate` ablation recovers the old `CX21-B` ceiling, confirming the gate is too conservative.
- `CX22-D` is the strongest repair: shadow adoption keeps most of the `flange` gain and cuts runtime from `3.216x` to `2.647x`, but it still leaves `maze / narrow_passage / parasol_misc` negative and therefore does not create a stable overall advantage regime.
- no `CX22` branch is promotable; accepted mainline remains `RS + refined CX3-D / RS-HPG`.
