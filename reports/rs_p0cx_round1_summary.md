# P0-CX Round-1 Summary

## CX-A
- params: `{'residual_alpha': 0.55, 'tube_open_gain': 0.25, 'tube_conservative_gain': 0.2}`
- public parasol exp3: success=`0.777778`, expansions=`2672.389`, time_ms=`569.491`
- public parasol exp4: success=`0.833333`, expansions=`5040.778`, time_ms=`1074.652`
- standard support: mp expansions=`137.506`, csm expansions=`348.205`
- same-alpha ablation: exp3 plain→cx delta=`12.722` expansions, exp4 plain→cx delta=`15.056` expansions, exp4 success delta=`0.000000`
- best family-level exp4 plain→cx delta: `parasol_misc` / `38.833` expansions

## CX-B
- params: `{'residual_alpha': 0.55, 'progress_gain': 0.4, 'off_corridor_dampen': 0.15}`
- public parasol exp3: success=`0.777778`, expansions=`2691.889`, time_ms=`571.718`
- public parasol exp4: success=`0.833333`, expansions=`5063.889`, time_ms=`1076.554`
- standard support: mp expansions=`137.461`, csm expansions=`348.090`
- same-alpha ablation: exp3 plain→cx delta=`-6.778` expansions, exp4 plain→cx delta=`-8.056` expansions, exp4 success delta=`0.000000`
- best family-level exp4 plain→cx delta: `narrow_passage` / `4.000` expansions

## CX-C
- params: `{'residual_alpha': 0.45, 'effort_gain': 0.35, 'safe_dampen': 0.3}`
- public parasol exp3: success=`0.777778`, expansions=`2681.667`, time_ms=`572.501`
- public parasol exp4: success=`0.833333`, expansions=`5051.556`, time_ms=`1075.700`
- standard support: mp expansions=`137.576`, csm expansions=`348.405`
- same-alpha ablation: exp3 plain→cx delta=`10.500` expansions, exp4 plain→cx delta=`13.000` expansions, exp4 success delta=`0.000000`
- best family-level exp4 plain→cx delta: `parasol_misc` / `38.833` expansions

## CX-D
- params: `{'residual_alpha': 0.55, 'n_proto': 3, 'mix_ratio': 0.2}`
- public parasol exp3: success=`0.777778`, expansions=`2690.778`, time_ms=`589.541`
- public parasol exp4: success=`0.833333`, expansions=`5065.333`, time_ms=`1111.571`
- standard support: mp expansions=`136.030`, csm expansions=`346.048`
- same-alpha ablation: exp3 plain→cx delta=`-5.667` expansions, exp4 plain→cx delta=`-9.500` expansions, exp4 success delta=`0.000000`
- best family-level exp4 plain→cx delta: `narrow_passage` / `5.750` expansions
