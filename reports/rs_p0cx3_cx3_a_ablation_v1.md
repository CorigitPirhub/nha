# CX3-A Ablation Report

- chosen params: `{'residual_alpha': 0.45, 'abstain_margin': 0.02, 'support_quantile': 0.9, 'penalty_gain': 1.4, 'corridor_bonus': 0.35}`

## EXP3
- CX3-A success=`0.722222` vs Plain=`0.777778` vs Full=`0.777778` vs No-Residual=`0.777778`
- CX3-A expansions=`2871.333` vs Plain=`2692.167` vs Full=`2668.222` vs No-Residual=`2784.167`
- CX3-A time_ms=`610.836` vs Plain=`574.409` vs Full=`996.500` vs No-Residual=`1041.709`

## EXP4
- CX3-A success=`0.833333` vs Plain=`0.833333` vs Ours=`1.000000` vs Hybrid=`1.000000`
- CX3-A expansions=`5190.222` vs Plain=`5064.556` vs Ours=`12177.278` vs Hybrid=`12368.111`
- CX3-A time_ms=`1104.364` vs Plain=`1075.579` vs Ours=`4537.729` vs Hybrid=`4611.133`