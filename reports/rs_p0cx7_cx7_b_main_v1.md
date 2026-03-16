# CX7-B P0-CX7 Trial Report

- chosen params: `{'misc_weight': 1.15, 'margin': 0.06, 'budget_ratio': 0.03, 'gain': 1.0}`

## Parasol Exp3 vs Frozen Baselines
- CX success: `0.777778` vs Full `0.777778` vs No-Residual `0.777778`
- CX expansions: `2687.833` vs Full `1430.571` vs No-Residual `1579.643`
- CX time: `566.465` vs Full `538.996` vs No-Residual `595.560`

## Parasol Exp4 vs Frozen Baselines
- CX success: `0.833333` vs Hybrid `1.000000` vs Full `1.000000`
- CX expansions: `5058.556` vs Hybrid `12368.111` vs Full `12177.278`
- CX time: `1072.350` vs Hybrid `4611.133` vs Full `4537.729`

## Standard Support vs Frozen Baselines
- mp: CX expansions=`139.442` vs A* `137.942` vs Full `137.515`; CX time=`0.676` vs A* `0.359` vs Full `25.759`
- csm: CX expansions=`359.973` vs A* `342.220` vs Full `348.192`; CX time=`1.495` vs A* `0.841` vs Full `30.424`