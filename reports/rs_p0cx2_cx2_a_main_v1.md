# CX2-A P0-CX2 Trial Report

- chosen params: `{'residual_alpha': 0.45, 'open_gain': 0.35, 'close_gain': 0.55, 'residual_trust': 0.15}`

## Parasol Exp3 vs Frozen Baselines
- CX success: `0.722222` vs Full `0.777778` vs No-Residual `0.777778`
- CX expansions: `2942.222` vs Full `1430.571` vs No-Residual `1579.643`
- CX time: `618.801` vs Full `538.996` vs No-Residual `595.560`

## Parasol Exp4 vs Frozen Baselines
- CX success: `0.777778` vs Hybrid `1.000000` vs Full `1.000000`
- CX expansions: `6010.333` vs Hybrid `12368.111` vs Full `12177.278`
- CX time: `1273.465` vs Hybrid `4611.133` vs Full `4537.729`

## Standard Support vs Frozen Baselines
- mp: CX expansions=`206.928` vs A* `137.942` vs Full `137.515`; CX time=`69.088` vs A* `0.359` vs Full `25.759`
- csm: CX expansions=`712.633` vs A* `342.220` vs Full `348.192`; CX time=`100.844` vs A* `0.841` vs Full `30.424`