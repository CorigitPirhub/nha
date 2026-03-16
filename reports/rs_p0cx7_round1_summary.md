# P0-CX7 Round-1 Summary

- accepted comparator: `RS + refined CX3-D / RS-HPG`
- additional lightweight bootstrap note for the best `CX7` candidate: `reports/rs_p0cx7_stats_v1.md`

## CX7-A
- params: `{'misc_weight': 0.85, 'uncert_weight': 0.2, 'support_weight': 0.2, 'margin': 0.02, 'budget_ratio': 0.02, 'gain': 0.8}`
- public exp3/exp4 success: `0.777778` / `0.833333`
- vs Plain-Residual expansions: exp3=`30.722`, exp4=`30.722`
- vs accepted CX3-D expansions: exp3=`-0.278`, exp4=`-0.278`
- subgroup vs CX3-D: misc=`15.167`, narrow=`-23.000`, flange=`-0.800`
- ordinary support: mp exp/time=`139.048`/`136.340`, csm exp/time=`356.267`/`225.727`

## CX7-B
- params: `{'misc_weight': 1.15, 'margin': 0.06, 'budget_ratio': 0.03, 'gain': 1.0}`
- public exp3/exp4 success: `0.777778` / `0.833333`
- vs Plain-Residual expansions: exp3=`-2.722`, exp4=`-2.722`
- vs accepted CX3-D expansions: exp3=`-33.722`, exp4=`-33.722`
- subgroup vs CX3-D: misc=`-103.167`, narrow=`0.000`, flange=`2.400`
- ordinary support: mp exp/time=`139.442`/`0.676`, csm exp/time=`359.973`/`1.495`

## CX7-D
- params: `{'arb_margin': 0.02, 'gain': 0.8}`
- public exp3/exp4 success: `0.777778` / `0.833333`
- vs Plain-Residual expansions: exp3=`25.056`, exp4=`-14.722`
- vs accepted CX3-D expansions: exp3=`-5.944`, exp4=`-45.722`
- subgroup vs CX3-D: misc=`-41.333`, narrow=`35.000`, flange=`-143.200`
- ordinary support: mp exp/time=`136.544`/`0.472`, csm exp/time=`351.363`/`1.192`

## CX7-C
- params: `{'cost_weight': 0.85, 'support_weight': 0.2, 'margin': 0.02, 'budget_ratio': 0.02, 'gain': 0.8}`
- public exp3/exp4 success: `0.777778` / `0.833333`
- vs Plain-Residual expansions: exp3=`36.889`, exp4=`36.889`
- vs accepted CX3-D expansions: exp3=`5.889`, exp4=`5.889`
- subgroup vs CX3-D: misc=`15.833`, narrow=`1.000`, flange=`1.400`
- ordinary support: mp exp/time=`140.506`/`0.775`, csm exp/time=`362.298`/`1.603`

## Round Conclusion
- No `CX7` candidate beats the accepted `CX3-D` branch by a decisive margin on the public `exp4` average expansion metric.
- `CX7-A` is the clearest evidence-accumulation / accountable-certification attempt, but it remains slightly worse than accepted `CX3-D`.
- `CX7-B` is not competitive and should be frozen as failure evidence.
- `CX7-D` also fails to beat the accepted branch and should not be promoted.
- `CX7-C` is the strongest of the new candidates: it is directionally slightly better than accepted `CX3-D` (`+5.889`), but the gain remains too small and statistically weak to justify a mainline promotion.
- Therefore no `CX7` candidate is promoted. The accepted mainline remains `RS cost field + refined CX3-D / RS-HPG`.