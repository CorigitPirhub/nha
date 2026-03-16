# CX5-B P0-CX5 Trial Report

- chosen params: `{'gain': 0.6, 'sim_temp': 3.0, 'top_quantile': 0.985}`

## Parasol Exp3 vs Frozen Baselines
- CX success: `0.722222` vs Full `0.777778` vs No-Residual `0.777778`
- CX expansions: `3009.444` vs Full `1430.571` vs No-Residual `1579.643`
- CX time: `421.857` vs Full `538.996` vs No-Residual `595.560`

## Parasol Exp4 vs Frozen Baselines
- CX success: `0.833333` vs Hybrid `1.000000` vs Full `1.000000`
- CX expansions: `5520.944` vs Hybrid `12368.111` vs Full `12177.278`
- CX time: `781.364` vs Hybrid `4611.133` vs Full `4537.729`

## Standard Support vs Frozen Baselines
- mp: CX expansions=`140.499` vs A* `137.942` vs Full `137.515`; CX time=`96.244` vs A* `0.359` vs Full `25.759`
- csm: CX expansions=`382.522` vs A* `342.220` vs Full `348.192`; CX time=`160.702` vs A* `0.841` vs Full `30.424`