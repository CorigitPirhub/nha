# P0-CX2 Round-1 Summary

## CX2-A
- params: `{'residual_alpha': 0.45, 'open_gain': 0.35, 'close_gain': 0.55, 'residual_trust': 0.15}`
- public parasol exp3: success=`0.722222`, expansions=`2942.222`, time_ms=`618.801`
- public parasol exp4: success=`0.777778`, expansions=`6010.333`, time_ms=`1273.465`
- standard support: mp expansions=`206.928`, csm expansions=`712.633`
- same-alpha ablation: exp3 plain→cx delta=`-250.056` expansions, exp4 plain→cx delta=`-945.778` expansions, exp4 success delta=`-0.055556`
- best exp4 family vs plain: `narrow_passage` / `181.250` expansions; worst family: `parasol_misc` / `-3027.167`

## CX2-B
- params: `{'residual_alpha': 0.45, 'off_bridge_gain': 2.0, 'bridge_pull_gain': 0.8}`
- public parasol exp3: success=`0.722222`, expansions=`2952.111`, time_ms=`633.174`
- public parasol exp4: success=`0.833333`, expansions=`5450.722`, time_ms=`1171.495`
- standard support: mp expansions=`159.726`, csm expansions=`409.158`
- same-alpha ablation: exp3 plain→cx delta=`-259.944` expansions, exp4 plain→cx delta=`-386.167` expansions, exp4 success delta=`0.000000`
- best exp4 family vs plain: `bug_trap` / `1.000` expansions; worst family: `flange` / `-639.400`

## CX2-C
- params: `{'residual_alpha': 0.45, 'barrier_gain': 2.8, 'exemption_gain': 0.5}`
- public parasol exp3: success=`0.777778`, expansions=`2951.444`, time_ms=`632.578`
- public parasol exp4: success=`0.833333`, expansions=`5306.000`, time_ms=`1129.816`
- standard support: mp expansions=`143.675`, csm expansions=`377.385`
- same-alpha ablation: exp3 plain→cx delta=`-259.278` expansions, exp4 plain→cx delta=`-241.444` expansions, exp4 success delta=`0.000000`
- best exp4 family vs plain: `flange` / `122.600` expansions; worst family: `parasol_misc` / `-795.167`

## CX2-D
- params: `{'residual_alpha': 0.55, 'capacity_gain': 0.25, 'risk_gain': 0.45, 'delta_gain': 0.85}`
- public parasol exp3: success=`0.388889`, expansions=`4404.111`, time_ms=`943.277`
- public parasol exp4: success=`0.555556`, expansions=`10783.333`, time_ms=`2303.581`
- standard support: mp expansions=`201.989`, csm expansions=`601.620`
- same-alpha ablation: exp3 plain→cx delta=`-1719.000` expansions, exp4 plain→cx delta=`-5727.500` expansions, exp4 success delta=`-0.277778`
- best exp4 family vs plain: `bug_trap` / `-5.000` expansions; worst family: `parasol_misc` / `-8478.667`

## Round Conclusion
- None of the four `CX2-*` candidates restored the public `parasol_narrow` success axis or beat same-alpha `Plain-Residual` on average expansions.
- `CX2-A` and `CX2-C` show localized expansion gains on `flange` (and for `CX2-A`, also on `narrow_passage`), but both lose badly on `parasol_misc`; this means the geometry/topology signal is not yet stable enough for a global claim.
- `CX2-B` preserves public success better than `CX2-A`, but is uniformly worse than `Plain-Residual` on expansions.
- `CX2-D` is decisively negative on both success and search effort.
- Because the public frozen bundle is already clearly negative, this round does not escalate any `CX2-*` candidate to the expanded `rs_root_hard_v2/test` benchmark.