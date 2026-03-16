# P0-CX23 Round1 Summary

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; this round stayed public-first and did not consume hard-test evidence

## Variant Readout
- `CX23-A`: calib_val exp_delta=`510.857`, calib_val overhead=`1.520833`, exp4 exp_delta=`340.500`, exp4 overhead=`1.686486`, flange exp_delta=`1421.400`
- `CX23-B`: calib_val exp_delta=`471.571`, calib_val overhead=`1.546203`, exp4 exp_delta=`326.333`, exp4 overhead=`1.580398`, flange exp_delta=`1424.000`
- `CX23-C`: calib_val exp_delta=`1218.571`, calib_val overhead=`1.297095`, exp4 exp_delta=`392.889`, exp4 overhead=`1.359640`, flange exp_delta=`1428.400`
- `CX23-D`: calib_val exp_delta=`471.571`, calib_val overhead=`1.506056`, exp4 exp_delta=`326.333`, exp4 overhead=`1.544657`, flange exp_delta=`1424.000`

## Ordering
- rank 1: `CX23-C`
- rank 2: `CX23-A`
- rank 3: `CX23-D`
- rank 4: `CX23-B`

## Readout
- `CX23-C` is the strongest branch in this round: it lifts public `exp4` to `+392.889`, keeps `flange = +1428.4`, turns `narrow_passage` positive at `+98.25`, and lowers overhead to `1.359640`, but `maze = -113.0` and `parasol_misc = -58.333` still block promotion.
- `CX23-A` is the best distillation branch: it improves over `CX22-D` on overall `exp4` and `parasol_misc`, but still leaves `maze / narrow_passage` negative and keeps runtime well above deployment budget.
- `CX23-B` and `CX23-D` do not materially improve over their ablations; the contrastive debias and counterfactual editor objects, as implemented here, do not yet create measurable new leverage.
- no `CX23` branch is promotable; accepted mainline remains `RS + refined CX3-D / RS-HPG`.
