# CX3-A P0-CX3 Trial Report

- chosen params: `{'residual_alpha': 0.45, 'abstain_margin': 0.02, 'support_quantile': 0.9, 'penalty_gain': 1.4, 'corridor_bonus': 0.35}`

## Parasol Exp3 vs Frozen Baselines
- CX success: `0.722222` vs Full `0.777778` vs No-Residual `0.777778`
- CX expansions: `2871.333` vs Full `1430.571` vs No-Residual `1579.643`
- CX time: `614.834` vs Full `538.996` vs No-Residual `595.560`

## Parasol Exp4 vs Frozen Baselines
- CX success: `0.833333` vs Hybrid `1.000000` vs Full `1.000000`
- CX expansions: `5190.222` vs Hybrid `12368.111` vs Full `12177.278`
- CX time: `1102.319` vs Hybrid `4611.133` vs Full `4537.729`

## Standard Support vs Frozen Baselines
- mp: CX expansions=`144.950` vs A* `137.942` vs Full `137.515`; CX time=`99.334` vs A* `0.359` vs Full `25.759`
- csm: CX expansions=`373.543` vs A* `342.220` vs Full `348.192`; CX time=`167.545` vs A* `0.841` vs Full `30.424`