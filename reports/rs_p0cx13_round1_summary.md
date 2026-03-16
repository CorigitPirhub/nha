# P0-CX13 Round1 Summary

- protocol: accepted `RS + CX3-D` field locked; CX13 layers trained on dev-only data and evaluated on public `parasol_narrow` after lock-in
- no `rs_root_hard_v2/test` evidence was consumed in this round

## Variant Readout
- `CX13-C`: calib_val exp_delta=`0.000`, calib_val overhead=`0.062417`, exp4 exp_delta=`0.000`, exp4 overhead=`0.565540`, flange exp_delta=`0.000`
- `CX13-B`: calib_val exp_delta=`0.000`, calib_val overhead=`0.283617`, exp4 exp_delta=`0.000`, exp4 overhead=`0.909466`, flange exp_delta=`0.000`
- `CX13-A`: calib_val exp_delta=`0.000`, calib_val overhead=`0.291722`, exp4 exp_delta=`0.000`, exp4 overhead=`0.915084`, flange exp_delta=`0.000`

## Ordering
- rank 1: `CX13-C`
- rank 2: `CX13-B`
- rank 3: `CX13-A`

## Round Verdict
- `CX13-A / RS-BBC`: basin budget control changes where search spends effort, but it only adds substantial runtime overhead while leaving expansions unchanged at public scale.
- `CX13-B / RS-IAS`: instance-adaptive search schedules also fail to create any measurable gain; the selected schedules mostly reparameterize the same accepted search without moving the frontier.
- `CX13-C / RS-TCB`: topological contracts are cheaper than the other two, but they still collapse to baseline tie with no positive `exp_delta`.
- Across all three routes, the common failure mode is **allocation without leverage**: the new computation-allocation objects do not create enough structural separation to outperform accepted `CX3-D`, yet some of them still add significant overhead.
- Therefore `CX13` does not clear the public gate, accepted mainline remains `RS + refined CX3-D / RS-HPG`, and even the non-sketch computation-allocation family has not yet opened a new advantage regime under the current protocol.