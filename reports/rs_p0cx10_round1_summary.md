# P0-CX10 Round1 Summary

- protocol: all variants selected on `calib_hard_v1`; public `parasol_narrow` and full `mp/csm` field audit were run post lock-in
- no `rs_root_hard_v2/test` evidence was consumed in this round because none of the four branches cleared the public parasol go/no-go gate

## Variant Readout
- `CX10-A`: calib_val exp_delta=`0.000`, calib_val overhead=`0.446955`, exp4 exp_delta=`0.000`, exp4 overhead=`1.188354`
- `CX10-B`: calib_val exp_delta=`0.000`, calib_val overhead=`-0.131064`, exp4 exp_delta=`0.000`, exp4 overhead=`0.331174`
- `CX10-C`: calib_val exp_delta=`-343.857`, calib_val overhead=`0.508193`, exp4 exp_delta=`-9.500`, exp4 overhead=`1.180549`
- `CX10-D`: calib_val exp_delta=`-20.143`, calib_val overhead=`-0.112479`, exp4 exp_delta=`-123.111`, exp4 overhead=`0.386410`


## Ordering
- rank 1: `CX10-B`
- rank 2: `CX10-A`
- rank 3: `CX10-C`
- rank 4: `CX10-D`

## Round Verdict
- `CX10-A / RS-CEC`: tied on public parasol but with very large overhead, so it does not beat accepted `CX3-D`.
- `CX10-B / RS-HBC`: tied on public parasol and slightly faster on `exp3`, but still incurs `~33%` overhead on `exp4`; it remains the least-bad branch but not a passing one.
- `CX10-C / RS-NFA`: harms both effort and runtime; the phase-controller attempt is a clear negative result.
- `CX10-D / RS-LAS`: keeps a small positive signal on `narrow_passage`, but public overall is negative because `flange` regresses strongly.
- Overall: none of the four `CX10` branches break the current Pareto deadlock, so `P0-CX` accepted mainline remains `RS + refined CX3-D / RS-HPG`.