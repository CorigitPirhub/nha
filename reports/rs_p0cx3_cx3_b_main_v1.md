# CX3-B P0-CX3 Trial Report

- chosen params: `{'residual_alpha': 0.55, 'abstain_margin': 0.0, 'corridor_gain': 0.35, 'separator_gain': 1.1, 'hard_gain': 0.55}`

## Parasol Exp3 vs Frozen Baselines
- CX success: `0.777778` vs Full `0.777778` vs No-Residual `0.777778`
- CX expansions: `2798.333` vs Full `1430.571` vs No-Residual `1579.643`
- CX time: `590.572` vs Full `538.996` vs No-Residual `595.560`

## Parasol Exp4 vs Frozen Baselines
- CX success: `0.833333` vs Hybrid `1.000000` vs Full `1.000000`
- CX expansions: `5127.944` vs Hybrid `12368.111` vs Full `12177.278`
- CX time: `1082.869` vs Hybrid `4611.133` vs Full `4537.729`

## Standard Support vs Frozen Baselines
- mp: CX expansions=`141.387` vs A* `137.942` vs Full `137.515`; CX time=`0.663` vs A* `0.359` vs Full `25.759`
- csm: CX expansions=`359.220` vs A* `342.220` vs Full `348.192`; CX time=`1.413` vs A* `0.841` vs Full `30.424`