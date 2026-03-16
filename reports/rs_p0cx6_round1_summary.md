# P0-CX6 Round-1 Summary

- accepted comparator: `RS + refined CX3-D / RS-HPG`
- additional lightweight bootstrap note for `CX6-D`: `reports/rs_p0cx6_stats_v1.md`

## CX6-A
- params: `{'misc_weight': 1.15, 'uncert_weight': 0.3, 'margin': 0.06, 'budget_ratio': 0.03, 'gain': 1.0}`
- public exp3/exp4 success: `0.777778` / `0.833333`
- vs Plain-Residual expansions: exp3=`30.333`, exp4=`30.333`
- vs accepted CX3-D expansions: exp3=`-0.667`, exp4=`-0.667`
- subgroup vs CX3-D: misc=`-1.667`, narrow=`0.000`, flange=`-0.400`
- ordinary support: mp exp/time=`138.281`/`96.375`, csm exp/time=`353.462`/`161.840`

## CX6-B
- params: `{'gain': 0.9, 'sim_temp': 4.0}`
- public exp3/exp4 success: `0.777778` / `0.833333`
- vs Plain-Residual expansions: exp3=`-186.667`, exp4=`-268.944`
- vs accepted CX3-D expansions: exp3=`-217.667`, exp4=`-299.944`
- subgroup vs CX3-D: misc=`-68.333`, narrow=`-151.500`, flange=`-875.400`
- ordinary support: mp exp/time=`143.852`/`0.539`, csm exp/time=`380.498`/`1.285`

## CX6-C
- params: `{'misc_weight': 0.8, 'uncert_weight': 0.15, 'margin': 0.02, 'budget_ratio': 0.02, 'gain': 0.8}`
- public exp3/exp4 success: `0.777778` / `0.833333`
- vs Plain-Residual expansions: exp3=`-38.444`, exp4=`-38.444`
- vs accepted CX3-D expansions: exp3=`-69.444`, exp4=`-69.444`
- subgroup vs CX3-D: misc=`-178.167`, narrow=`-4.250`, flange=`-30.800`
- ordinary support: mp exp/time=`139.054`/`0.521`, csm exp/time=`359.215`/`1.109`

## CX6-D
- params: `{'gain': 1.1, 'misc_weight': 1.1}`
- public exp3/exp4 success: `0.777778` / `0.833333`
- vs Plain-Residual expansions: exp3=`31.611`, exp4=`31.611`
- vs accepted CX3-D expansions: exp3=`0.611`, exp4=`0.611`
- subgroup vs CX3-D: misc=`1.833`, narrow=`0.000`, flange=`0.000`
- ordinary support: mp exp/time=`137.312`/`0.371`, csm exp/time=`349.420`/`0.862`

## Round Conclusion
- No `CX6` candidate beats the accepted `CX3-D` branch by a decisive margin on the public `exp4` average expansion metric.
- `CX6-A` is the clearest accountable-intervention attempt, but it remains slightly worse than `CX3-D` on the public bundle.
- `CX6-B` is clearly negative and should be frozen as failure evidence.
- `CX6-C` remains too conservative and underperforms accepted `CX3-D`.
- `CX6-D` is the most promising follow-up: it slightly improves over accepted `CX3-D` on average expansions (`+0.611`), but the gain is too small to justify promotion; the lightweight bootstrap note confirms it is only a weak positive follow-up, not a new mainline.
- Therefore no `CX6` candidate is promoted. The accepted mainline remains `RS cost field + refined CX3-D / RS-HPG`.