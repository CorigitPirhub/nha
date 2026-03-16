# CX3-D Aux Follow-up Note

Status: `rejected-followup`
Date: `2026-03-08`

This note records a targeted `CX3-D` follow-up that injected a guarded auxiliary hard-family positive term borrowed from `CX3-C` signals.

## Main report

# CX3-D P0-CX3 Trial Report

- chosen params: `{'residual_alpha': 0.55, 'abstain_margin': 0.1, 'guard_radius_m': 1.6, 'penalty_gain': 1.3, 'aux_positive_gain': 0.35, 'misc_veto_gain': 0.65}`

## Parasol Exp3 vs Frozen Baselines
- CX success: `0.777778` vs Full `0.777778` vs No-Residual `0.777778`
- CX expansions: `2663.000` vs Full `1430.571` vs No-Residual `1579.643`
- CX time: `563.558` vs Full `538.996` vs No-Residual `595.560`

## Parasol Exp4 vs Frozen Baselines
- CX success: `0.833333` vs Hybrid `1.000000` vs Full `1.000000`
- CX expansions: `5033.667` vs Hybrid `12368.111` vs Full `12177.278`
- CX time: `1072.266` vs Hybrid `4611.133` vs Full `4537.729`

## Standard Support vs Frozen Baselines
- mp: CX expansions=`139.476` vs A* `137.942` vs Full `137.515`; CX time=`99.197` vs A* `0.359` vs Full `25.759`
- csm: CX expansions=`359.212` vs A* `342.220` vs Full `348.192`; CX time=`167.625` vs A* `0.841` vs Full `30.424`

## Ablation report

# CX3-D Ablation Report

- chosen params: `{'residual_alpha': 0.55, 'abstain_margin': 0.1, 'guard_radius_m': 1.6, 'penalty_gain': 1.3, 'aux_positive_gain': 0.35, 'misc_veto_gain': 0.65}`

## EXP3
- CX3-D success=`0.777778` vs Plain=`0.777778` vs Full=`0.777778` vs No-Residual=`0.777778`
- CX3-D expansions=`2663.000` vs Plain=`2685.111` vs Full=`2668.222` vs No-Residual=`2784.167`
- CX3-D time_ms=`568.887` vs Plain=`572.907` vs Full=`996.500` vs No-Residual=`1041.709`

## EXP4
- CX3-D success=`0.833333` vs Plain=`0.833333` vs Ours=`1.000000` vs Hybrid=`1.000000`
- CX3-D expansions=`5033.667` vs Plain=`5055.833` vs Ours=`12177.278` vs Hybrid=`12368.111`
- CX3-D time_ms=`1076.149` vs Plain=`1078.309` vs Ours=`4537.729` vs Hybrid=`4611.133`

## Decision

- The follow-up did not change public success, but only slightly changed average expansions.
- It significantly increased `mp/csm` runtime due the heavier auxiliary signal extraction, which makes it inferior to the simpler `CX3-D` baseline as the main conservative branch.
- Therefore this variant is rejected and not used as the accepted `CX3-D` evidence.
