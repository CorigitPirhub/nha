# P0-CX5 Round-1 Summary

## CX5-A
- params: `{'beta': 1.05, 'margin': 0.06, 'budget_ratio': 0.03, 'gain': 1.0}`
- public exp3/exp4 success: `0.777778` / `0.833333`
- vs Plain-Residual expansions: exp3=`-2.833`, exp4=`-2.833`
- vs accepted CX3-D expansions: exp3=`-33.833`, exp4=`-33.833`
- subgroup vs CX3-D: misc=`-101.500`, narrow=`0.000`, flange=`0.000`
- ordinary support: mp exp/time=`138.846`/`95.803`, csm exp/time=`356.423`/`159.692`

## CX5-B
- params: `{'gain': 0.6, 'sim_temp': 3.0, 'top_quantile': 0.985}`
- public exp3/exp4 success: `0.722222` / `0.833333`
- vs Plain-Residual expansions: exp3=`-324.333`, exp4=`-465.111`
- vs accepted CX3-D expansions: exp3=`-355.333`, exp4=`-496.111`
- subgroup vs CX3-D: misc=`-453.500`, narrow=`-187.000`, flange=`-1084.400`
- ordinary support: mp exp/time=`140.499`/`96.244`, csm exp/time=`382.522`/`160.702`

## CX5-C
- params: `{'misc_budget': 0.1, 'max_atoms': 2, 'gain': 1.1}`
- public exp3/exp4 success: `0.777778` / `0.833333`
- vs Plain-Residual expansions: exp3=`31.000`, exp4=`31.000`
- vs accepted CX3-D expansions: exp3=`0.000`, exp4=`0.000`
- subgroup vs CX3-D: misc=`0.000`, narrow=`0.000`, flange=`0.000`
- ordinary support: mp exp/time=`137.321`/`0.617`, csm exp/time=`349.488`/`1.201`

## CX5-D
- params: `{'misc_weight': 1.3, 'hard_gain': 1.1, 'margin': 0.08}`
- public exp3/exp4 success: `0.777778` / `0.833333`
- vs Plain-Residual expansions: exp3=`30.667`, exp4=`30.667`
- vs accepted CX3-D expansions: exp3=`-0.333`, exp4=`-0.333`
- subgroup vs CX3-D: misc=`0.000`, narrow=`-1.500`, flange=`0.000`
- ordinary support: mp exp/time=`137.338`/`136.727`, csm exp/time=`349.848`/`226.379`

## Round Conclusion
- No `CX5` candidate beats the accepted `CX3-D` branch on the public `exp4` average expansion metric.
- `CX5-A` and `CX5-D` are closest in spirit to the accepted line, but both are slightly worse than `CX3-D` on the public bundle.
- `CX5-C` effectively collapses to the accepted `CX3-D` behavior and adds no new value.
- `CX5-B` is clearly negative and should be frozen as failure evidence.
- Therefore no `CX5` candidate is promoted. The accepted mainline remains `RS cost field + refined CX3-D / RS-HPG`.