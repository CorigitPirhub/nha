# P0-CX14 Round1 Summary

- protocol: accepted `RS + CX3-D` field locked; CX14 layers trained on dev-only data and evaluated on public `parasol_narrow` after lock-in
- no `rs_root_hard_v2/test` evidence was consumed in this round

## Variant Readout
- `CX14-B`: calib_val exp_delta=`7.000`, calib_val overhead=`1.471205`, exp4 exp_delta=`0.444`, exp4 overhead=`1.582221`, flange exp_delta=`1.000`
- `CX14-A`: calib_val exp_delta=`6.571`, calib_val overhead=`1.606644`, exp4 exp_delta=`0.389`, exp4 overhead=`1.709200`, flange exp_delta=`0.600`
- `CX14-C`: calib_val exp_delta=`6.571`, calib_val overhead=`1.749977`, exp4 exp_delta=`0.389`, exp4 overhead=`1.854265`, flange exp_delta=`0.600`

## Ordering
- rank 1: `CX14-B`
- rank 2: `CX14-A`
- rank 3: `CX14-C`

## Round Verdict
- `CX14-B / RS-LHU` is the current best surviving branch: it produces the strongest public `exp4` signal (`+0.444`) and keeps `flange` non-negative (`+1.0`), but its runtime overhead is still extreme (`+158%`).
- `CX14-A / RS-NSG` and `CX14-C / RS-MHQ` also preserve small positive signals, which is notable because this is the first post-CX8 family that does more than pure tie-baseline on public `parasol_narrow`.
- However, all three branches are far outside the deployment envelope; the main bottleneck has shifted from “can we get signal?” to “can we make episode-local search memory cheap enough?”.
- Therefore `CX14` does not pass the public gate yet, accepted mainline remains `RS + refined CX3-D / RS-HPG`, but the route should remain **alive** as the current best surviving family rather than being frozen immediately.