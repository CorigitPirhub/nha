# P0-CX12 Round1 Summary

- protocol: base sketch locked from `CX10-D`; new CX12 layers trained on dev-only data and evaluated on public `parasol_narrow` after lock-in
- no `rs_root_hard_v2/test` evidence was consumed in this round

## Variant Readout
- `CX12-A`: calib_val exp_delta=`0.000`, calib_val overhead=`-0.021065`, exp4 exp_delta=`0.000`, exp4 overhead=`-0.008594`, flange exp_delta=`0.000`
- `CX12-C`: calib_val exp_delta=`0.000`, calib_val overhead=`-0.015912`, exp4 exp_delta=`0.000`, exp4 overhead=`0.000538`, flange exp_delta=`0.000`
- `CX12-B`: calib_val exp_delta=`0.000`, calib_val overhead=`-0.007387`, exp4 exp_delta=`0.000`, exp4 overhead=`0.006195`, flange exp_delta=`0.000`

## Ordering
- rank 1: `CX12-A`
- rank 2: `CX12-C`
- rank 3: `CX12-B`

## Round Verdict
- `CX12-A / RS-GHF`: geometry hard filter cleanly removes the flange collapse, but it does so by hard-vetoing all sketch activations that previously produced positive `narrow_passage` gains; overall it ties `CX3-D`.
- `CX12-C / RS-SSG`: search-state gating behaves almost identically to the hard filter; the extra state logic does not recover any positive signal over the geometry veto.
- `CX12-B / RS-CSA`: signed adjustment also collapses to a near-neutral intervention; the negative branch prevents harm, but the positive branch never survives strongly enough to move overall expansions.
- Across all three routes, the dominant failure mode is now **evidence saturation**: the new trap-aware filters are strong enough to erase harm, but the available dev-learned evidence is still too weak to preserve the sparse positive sketch wins.
- Therefore `CX12` does not clear the public gate, accepted mainline remains `RS + refined CX3-D / RS-HPG`, and the current flange-vs-narrow sketch-repair family is exhausted under the present protocol.