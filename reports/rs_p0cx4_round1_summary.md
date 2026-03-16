# P0-CX4 Round-1 Summary

## CX4-A
- params: `{'dual_lambda': 1.05, 'dual_margin': 0.08, 'budget_ratio': 0.03, 'gain': 1.0}`
- public exp3/exp4 success: `0.777778` / `0.833333`
- vs Plain-Residual expansions: exp3=`34.056`, exp4=`-13.778`
- vs CX3-D expansions: exp3=`3.056`, exp4=`-44.778`
- subgroup vs CX3-D: misc=`-19.667`, flange=`-172.200`, narrow=`42.500`
- ordinary support: mp exp/time=`140.488`/`138.061`, csm exp/time=`367.540`/`229.300`

## CX4-D
- params: `{'beta': 1.1, 'margin': 0.08, 'budget_ratio': 0.035, 'gain': 1.1}`
- public exp3/exp4 success: `0.777778` / `0.833333`
- vs Plain-Residual expansions: exp3=`-26.833`, exp4=`-26.833`
- vs CX3-D expansions: exp3=`-57.833`, exp4=`-57.833`
- subgroup vs CX3-D: misc=`-160.833`, flange=`-0.200`, narrow=`-18.750`
- ordinary support: mp exp/time=`138.571`/`0.620`, csm exp/time=`354.957`/`1.381`

## CX4-C
- params: `{'risk_lambda': 1.2, 'budget_base': 0.02, 'budget_gain': 0.035, 'gain': 1.1}`
- public exp3/exp4 success: `0.777778` / `0.833333`
- vs Plain-Residual expansions: exp3=`43.222`, exp4=`6.278`
- vs CX3-D expansions: exp3=`12.222`, exp4=`-24.722`
- subgroup vs CX3-D: misc=`12.500`, flange=`-133.000`, narrow=`36.000`
- ordinary support: mp exp/time=`140.491`/`0.573`, csm exp/time=`367.105`/`1.360`

## CX4-B
- params: `{'gain': 1.0, 'sim_temp': 5.0, 'top_quantile': 0.99}`
- public exp3/exp4 success: `0.777778` / `0.833333`
- vs Plain-Residual expansions: exp3=`31.000`, exp4=`31.000`
- vs CX3-D expansions: exp3=`0.000`, exp4=`0.000`
- subgroup vs CX3-D: misc=`0.000`, flange=`0.000`, narrow=`0.000`
- ordinary support: mp exp/time=`137.321`/`137.609`, csm exp/time=`349.488`/`226.028`

## Round Conclusion
- No `CX4` candidate beats the accepted `CX3-D` branch on the public `exp4` average expansion metric.
- `CX4-A` and `CX4-C` can still improve over `Plain-Residual`, but neither is strong enough to displace `CX3-D`; both also give up too much on either `flange` or ordinary-scene overhead.
- `CX4-D` is conceptually closest to the desired baseline-relative route, but its current implementation is simply weaker than the accepted `CX3-D` guard.
- `CX4-B` effectively collapses back to the accepted `CX3-D` branch and adds no new value.
- Therefore no `CX4` candidate is promoted to the main accepted line in this round. The accepted mainline remains `RS cost field + refined CX3-D / RS-HPG`.