# P0-CX11 Round1 Summary

- protocol: base sketch locked from `CX10-D`; new CX11 layers trained on dev-only data and evaluated on public `parasol_narrow` after lock-in
- no `rs_root_hard_v2/test` evidence was consumed in this round

## Variant Readout
- `CX11-A`: calib_val exp_delta=`0.000`, calib_val overhead=`-0.050230`, exp4 exp_delta=`0.000`, exp4 overhead=`-0.046181`, flange exp_delta=`0.000`
- `CX11-C`: calib_val exp_delta=`0.000`, calib_val overhead=`-0.037368`, exp4 exp_delta=`0.000`, exp4 overhead=`-0.035979`, flange exp_delta=`0.000`
- `CX11-B`: calib_val exp_delta=`0.000`, calib_val overhead=`0.014645`, exp4 exp_delta=`0.000`, exp4 overhead=`0.013676`, flange exp_delta=`0.000`

## Ordering
- rank 1: `CX11-A`
- rank 2: `CX11-C`
- rank 3: `CX11-B`

## Round Verdict
- `CX11-B / RS-LDS`: removes the `flange` regression but does so by learning to defer almost everything back to accepted `CX3-D`; public overall becomes an exact tie.
- `CX11-C / RS-CSV`: token-level verifier also collapses to near-complete abstention; it is safer than `CX10-D`, but it does not preserve the `narrow_passage` gain.
- `CX11-A / RS-RST`: typed token redesign behaves similarly, acting as a stronger abstention layer rather than a gain-preserving token system.
- Across all three routes, the dominant failure mode is **over-deferral**: the new layers successfully erase `flange` harm but also erase all positive semantic signal.
- Therefore `CX11` does not clear the public gate, accepted mainline remains `RS + refined CX3-D / RS-HPG`, and the current sketch/defer family is exhausted under the present protocol.