# CX-B P0-CX Trial Report

- chosen params: `{'residual_alpha': 0.55, 'progress_gain': 0.4, 'off_corridor_dampen': 0.15}`

## Parasol Exp3 vs Frozen Baselines
- CX success: `0.777778` vs Full `0.777778` vs No-Residual `0.777778`
- CX expansions: `2691.889` vs Full `1430.571` vs No-Residual `1579.643`
- CX time: `571.718` vs Full `538.996` vs No-Residual `595.560`

## Parasol Exp4 vs Frozen Baselines
- CX success: `0.833333` vs Hybrid `1.000000` vs Full `1.000000`
- CX expansions: `5063.889` vs Hybrid `12368.111` vs Full `12177.278`
- CX time: `1076.554` vs Hybrid `4611.133` vs Full `4537.729`

## Standard Support vs Frozen Baselines
- mp: CX expansions=`137.461` vs A* `137.942` vs Full `137.515`; CX time=`2.570` vs A* `0.359` vs Full `25.759`
- csm: CX expansions=`348.090` vs A* `342.220` vs Full `348.192`; CX time=`3.645` vs A* `0.841` vs Full `30.424`