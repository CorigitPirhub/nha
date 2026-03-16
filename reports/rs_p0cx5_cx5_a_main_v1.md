# CX5-A P0-CX5 Trial Report

- chosen params: `{'beta': 1.05, 'margin': 0.06, 'budget_ratio': 0.03, 'gain': 1.0}`

## Parasol Exp3 vs Frozen Baselines
- CX success: `0.777778` vs Full `0.777778` vs No-Residual `0.777778`
- CX expansions: `2687.944` vs Full `1430.571` vs No-Residual `1579.643`
- CX time: `457.815` vs Full `538.996` vs No-Residual `595.560`

## Parasol Exp4 vs Frozen Baselines
- CX success: `0.833333` vs Hybrid `1.000000` vs Full `1.000000`
- CX expansions: `5058.667` vs Hybrid `12368.111` vs Full `12177.278`
- CX time: `845.816` vs Hybrid `4611.133` vs Full `4537.729`

## Standard Support vs Frozen Baselines
- mp: CX expansions=`138.846` vs A* `137.942` vs Full `137.515`; CX time=`95.803` vs A* `0.359` vs Full `25.759`
- csm: CX expansions=`356.423` vs A* `342.220` vs Full `348.192`; CX time=`159.692` vs A* `0.841` vs Full `30.424`