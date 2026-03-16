# CX7-A P0-CX7 Trial Report

- chosen params: `{'misc_weight': 0.85, 'uncert_weight': 0.2, 'support_weight': 0.2, 'margin': 0.02, 'budget_ratio': 0.02, 'gain': 0.8}`

## Parasol Exp3 vs Frozen Baselines
- CX success: `0.777778` vs Full `0.777778` vs No-Residual `0.777778`
- CX expansions: `2654.389` vs Full `1430.571` vs No-Residual `1579.643`
- CX time: `561.599` vs Full `538.996` vs No-Residual `595.560`

## Parasol Exp4 vs Frozen Baselines
- CX success: `0.833333` vs Hybrid `1.000000` vs Full `1.000000`
- CX expansions: `5025.111` vs Hybrid `12368.111` vs Full `12177.278`
- CX time: `1066.630` vs Hybrid `4611.133` vs Full `4537.729`

## Standard Support vs Frozen Baselines
- mp: CX expansions=`139.048` vs A* `137.942` vs Full `137.515`; CX time=`136.340` vs A* `0.359` vs Full `25.759`
- csm: CX expansions=`356.267` vs A* `342.220` vs Full `348.192`; CX time=`225.727` vs A* `0.841` vs Full `30.424`