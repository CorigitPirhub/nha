# CX3-B Ablation Report

- chosen params: `{'residual_alpha': 0.55, 'abstain_margin': 0.0, 'corridor_gain': 0.35, 'separator_gain': 1.1, 'hard_gain': 0.55}`

## EXP3
- CX3-B success=`0.777778` vs Plain=`0.777778` vs Full=`0.777778` vs No-Residual=`0.777778`
- CX3-B expansions=`2798.333` vs Plain=`2685.111` vs Full=`2668.222` vs No-Residual=`2784.167`
- CX3-B time_ms=`597.596` vs Plain=`574.015` vs Full=`996.500` vs No-Residual=`1041.709`

## EXP4
- CX3-B success=`0.833333` vs Plain=`0.833333` vs Ours=`1.000000` vs Hybrid=`1.000000`
- CX3-B expansions=`5127.944` vs Plain=`5055.833` vs Ours=`12177.278` vs Hybrid=`12368.111`
- CX3-B time_ms=`1089.349` vs Plain=`1077.547` vs Ours=`4537.729` vs Hybrid=`4611.133`