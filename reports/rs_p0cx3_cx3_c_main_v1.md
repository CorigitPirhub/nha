# CX3-C P0-CX3 Trial Report

- chosen params: `{'residual_alpha': 0.45, 'abstain_margin': 0.0, 'positive_gain': 1.1, 'negative_gain': 0.25, 'misc_veto_gain': 0.45}`

## Parasol Exp3 vs Frozen Baselines
- CX success: `0.777778` vs Full `0.777778` vs No-Residual `0.777778`
- CX expansions: `2740.167` vs Full `1430.571` vs No-Residual `1579.643`
- CX time: `389.233` vs Full `538.996` vs No-Residual `595.560`

## Parasol Exp4 vs Frozen Baselines
- CX success: `0.833333` vs Hybrid `1.000000` vs Full `1.000000`
- CX expansions: `5100.222` vs Hybrid `12368.111` vs Full `12177.278`
- CX time: `727.585` vs Hybrid `4611.133` vs Full `4537.729`

## Standard Support vs Frozen Baselines
- mp: CX expansions=`139.708` vs A* `137.942` vs Full `137.515`; CX time=`67.923` vs A* `0.359` vs Full `25.759`
- csm: CX expansions=`356.428` vs A* `342.220` vs Full `348.192`; CX time=`113.316` vs A* `0.841` vs Full `30.424`