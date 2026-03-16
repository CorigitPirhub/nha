# CX2-D P0-CX2 Trial Report

- chosen params: `{'residual_alpha': 0.55, 'capacity_gain': 0.25, 'risk_gain': 0.45, 'delta_gain': 0.85}`

## Parasol Exp3 vs Frozen Baselines
- CX success: `0.388889` vs Full `0.777778` vs No-Residual `0.777778`
- CX expansions: `4404.111` vs Full `1430.571` vs No-Residual `1579.643`
- CX time: `943.277` vs Full `538.996` vs No-Residual `595.560`

## Parasol Exp4 vs Frozen Baselines
- CX success: `0.555556` vs Hybrid `1.000000` vs Full `1.000000`
- CX expansions: `10783.333` vs Hybrid `12368.111` vs Full `12177.278`
- CX time: `2303.581` vs Hybrid `4611.133` vs Full `4537.729`

## Standard Support vs Frozen Baselines
- mp: CX expansions=`201.989` vs A* `137.942` vs Full `137.515`; CX time=`23.787` vs A* `0.359` vs Full `25.759`
- csm: CX expansions=`601.620` vs A* `342.220` vs Full `348.192`; CX time=`936.482` vs A* `0.841` vs Full `30.424`