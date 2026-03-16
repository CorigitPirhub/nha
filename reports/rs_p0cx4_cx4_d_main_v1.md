# CX4-D P0-CX4 Trial Report

- chosen params: `{'beta': 1.1, 'margin': 0.08, 'budget_ratio': 0.035, 'gain': 1.1}`

## Parasol Exp3 vs Frozen Baselines
- CX success: `0.777778` vs Full `0.777778` vs No-Residual `0.777778`
- CX expansions: `2711.944` vs Full `1430.571` vs No-Residual `1579.643`
- CX time: `601.506` vs Full `538.996` vs No-Residual `595.560`

## Parasol Exp4 vs Frozen Baselines
- CX success: `0.833333` vs Hybrid `1.000000` vs Full `1.000000`
- CX expansions: `5082.667` vs Hybrid `12368.111` vs Full `12177.278`
- CX time: `1120.793` vs Hybrid `4611.133` vs Full `4537.729`

## Standard Support vs Frozen Baselines
- mp: CX expansions=`138.571` vs A* `137.942` vs Full `137.515`; CX time=`0.620` vs A* `0.359` vs Full `25.759`
- csm: CX expansions=`354.957` vs A* `342.220` vs Full `348.192`; CX time=`1.381` vs A* `0.841` vs Full `30.424`