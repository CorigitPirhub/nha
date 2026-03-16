# CX6-A P0-CX6 Trial Report

- chosen params: `{'misc_weight': 1.15, 'uncert_weight': 0.3, 'margin': 0.06, 'budget_ratio': 0.03, 'gain': 1.0}`

## Parasol Exp3 vs Frozen Baselines
- CX success: `0.777778` vs Full `0.777778` vs No-Residual `0.777778`
- CX expansions: `2654.778` vs Full `1430.571` vs No-Residual `1579.643`
- CX time: `374.676` vs Full `538.996` vs No-Residual `595.560`

## Parasol Exp4 vs Frozen Baselines
- CX success: `0.833333` vs Hybrid `1.000000` vs Full `1.000000`
- CX expansions: `5025.500` vs Hybrid `12368.111` vs Full `12177.278`
- CX time: `711.536` vs Hybrid `4611.133` vs Full `4537.729`

## Standard Support vs Frozen Baselines
- mp: CX expansions=`138.281` vs A* `137.942` vs Full `137.515`; CX time=`96.375` vs A* `0.359` vs Full `25.759`
- csm: CX expansions=`353.462` vs A* `342.220` vs Full `348.192`; CX time=`161.840` vs A* `0.841` vs Full `30.424`