# CX4-A P0-CX4 Trial Report

- chosen params: `{'dual_lambda': 1.05, 'dual_margin': 0.08, 'budget_ratio': 0.03, 'gain': 1.0}`

## Parasol Exp3 vs Frozen Baselines
- CX success: `0.777778` vs Full `0.777778` vs No-Residual `0.777778`
- CX expansions: `2651.056` vs Full `1430.571` vs No-Residual `1579.643`
- CX time: `586.393` vs Full `538.996` vs No-Residual `595.560`

## Parasol Exp4 vs Frozen Baselines
- CX success: `0.833333` vs Hybrid `1.000000` vs Full `1.000000`
- CX expansions: `5069.611` vs Hybrid `12368.111` vs Full `12177.278`
- CX time: `1117.650` vs Hybrid `4611.133` vs Full `4537.729`

## Standard Support vs Frozen Baselines
- mp: CX expansions=`140.488` vs A* `137.942` vs Full `137.515`; CX time=`138.061` vs A* `0.359` vs Full `25.759`
- csm: CX expansions=`367.540` vs A* `342.220` vs Full `348.192`; CX time=`229.300` vs A* `0.841` vs Full `30.424`