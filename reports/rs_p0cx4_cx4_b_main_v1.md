# CX4-B P0-CX4 Trial Report

- chosen params: `{'gain': 1.0, 'sim_temp': 5.0, 'top_quantile': 0.99}`

## Parasol Exp3 vs Frozen Baselines
- CX success: `0.777778` vs Full `0.777778` vs No-Residual `0.777778`
- CX expansions: `2654.111` vs Full `1430.571` vs No-Residual `1579.643`
- CX time: `564.520` vs Full `538.996` vs No-Residual `595.560`

## Parasol Exp4 vs Frozen Baselines
- CX success: `0.833333` vs Hybrid `1.000000` vs Full `1.000000`
- CX expansions: `5024.833` vs Hybrid `12368.111` vs Full `12177.278`
- CX time: `1066.504` vs Hybrid `4611.133` vs Full `4537.729`

## Standard Support vs Frozen Baselines
- mp: CX expansions=`137.321` vs A* `137.942` vs Full `137.515`; CX time=`137.609` vs A* `0.359` vs Full `25.759`
- csm: CX expansions=`349.488` vs A* `342.220` vs Full `348.192`; CX time=`226.028` vs A* `0.841` vs Full `30.424`