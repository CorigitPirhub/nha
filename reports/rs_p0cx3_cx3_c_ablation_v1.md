# CX3-C Ablation Report

- chosen params: `{'residual_alpha': 0.45, 'abstain_margin': 0.0, 'positive_gain': 1.1, 'negative_gain': 0.25, 'misc_veto_gain': 0.45}`

## EXP3
- CX3-C success=`0.777778` vs Plain=`0.777778` vs Full=`0.777778` vs No-Residual=`0.777778`
- CX3-C expansions=`2740.167` vs Plain=`2692.167` vs Full=`2668.222` vs No-Residual=`2784.167`
- CX3-C time_ms=`435.565` vs Plain=`423.656` vs Full=`996.500` vs No-Residual=`1041.709`

## EXP4
- CX3-C success=`0.833333` vs Plain=`0.833333` vs Ours=`1.000000` vs Hybrid=`1.000000`
- CX3-C expansions=`5100.222` vs Plain=`5064.556` vs Ours=`12177.278` vs Hybrid=`12368.111`
- CX3-C time_ms=`775.105` vs Plain=`763.849` vs Ours=`4537.729` vs Hybrid=`4611.133`