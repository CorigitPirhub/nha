# P0-CX3 Round-1 Summary

- environment: `/home/zzy/anaconda3/envs/algo_distill/bin/python` (`torch 2.5.0+cu118`)
- note 1: an earlier base-Python CPU-only run was discarded and is not used as evidence.
- note 2: a root-cause bug in `rs_cx3/common.py` (`hard_likelihood/misc_likelihood` collapsed to zero due scalar `normalize01`) was discovered and fixed; all accepted evidence below is **after** that fix.
- note 3: a targeted `CX3-D` follow-up that injected `CX3-C`-style auxiliary positive signals was attempted and rejected because it significantly increased `mp/csm` runtime without improving the public claim (`reports/rs_p0cx3_cx3_d_aux_followup_v1.md`).
- note 4: the final accepted `CX3-D` evidence also includes a narrower conservative refinement (`low_bridge_scale`) that reduces ordinary-scene overhead while keeping the same public success semantics.
- note 5: statistical reinforcement is reported separately in `reports/rs_p0cx3_stats_v1.md`.

## CX3-A
- params: `{'residual_alpha': 0.45, 'abstain_margin': 0.02, 'support_quantile': 0.9, 'penalty_gain': 1.4, 'corridor_bonus': 0.35}`
- public parasol exp3: success=`0.722222`, expansions=`2871.333`, time_ms=`614.834`
- public parasol exp4: success=`0.833333`, expansions=`5190.222`, time_ms=`1102.319`
- standard support: mp expansions=`144.950` / time=`99.334`, csm expansions=`373.543` / time=`167.545`
- same-alpha ablation: exp3 plain→cx delta=`-179.167`, exp4 plain→cx delta=`-125.667`, exp4 success delta=`0.000000`
- protected subgroup check: misc exp delta=`-420.500`, misc success delta=`0.000000`
- hard-family check: flange exp delta=`205.200`, narrow exp delta=`-191.500`

## CX3-B
- params: `{'residual_alpha': 0.55, 'abstain_margin': 0.0, 'corridor_gain': 0.35, 'separator_gain': 1.1, 'hard_gain': 0.55}`
- public parasol exp3: success=`0.777778`, expansions=`2798.333`, time_ms=`590.572`
- public parasol exp4: success=`0.833333`, expansions=`5127.944`, time_ms=`1082.869`
- standard support: mp expansions=`141.387` / time=`0.663`, csm expansions=`359.220` / time=`1.413`
- same-alpha ablation: exp3 plain→cx delta=`-113.222`, exp4 plain→cx delta=`-72.111`, exp4 success delta=`0.000000`
- protected subgroup check: misc exp delta=`-235.500`, misc success delta=`0.000000`
- hard-family check: flange exp delta=`148.000`, narrow exp delta=`-156.250`

## CX3-C
- params: `{'residual_alpha': 0.45, 'abstain_margin': 0.0, 'positive_gain': 1.1, 'negative_gain': 0.25, 'misc_veto_gain': 0.45}`
- public parasol exp3: success=`0.777778`, expansions=`2740.167`, time_ms=`389.233`
- public parasol exp4: success=`0.833333`, expansions=`5100.222`, time_ms=`727.585`
- standard support: mp expansions=`139.708` / time=`67.923`, csm expansions=`356.428` / time=`113.316`
- same-alpha ablation: exp3 plain→cx delta=`-48.000`, exp4 plain→cx delta=`-35.667`, exp4 success delta=`0.000000`
- protected subgroup check: misc exp delta=`-173.833`, misc success delta=`0.000000`
- hard-family check: flange exp delta=`44.400`, narrow exp delta=`44.500`

## CX3-D
- params: `{'residual_alpha': 0.55, 'abstain_margin': 0.1, 'guard_radius_m': 1.6, 'penalty_gain': 1.3, 'low_bridge_thr': 0.06, 'low_bridge_scale': 0.25}`
- public parasol exp3: success=`0.777778`, expansions=`2654.111`, time_ms=`558.250`
- public parasol exp4: success=`0.833333`, expansions=`5024.833`, time_ms=`1058.671`
- standard support: mp expansions=`137.321` / time=`38.152`, csm expansions=`349.488` / time=`61.134`
- same-alpha ablation: exp3 plain→cx delta=`31.000`, exp4 plain→cx delta=`31.000`, exp4 success delta=`0.000000`
- protected subgroup check: misc exp delta=`104.000`, misc success delta=`0.000000`
- hard-family check: flange exp delta=`0.000`, narrow exp delta=`-16.500`

## Round Conclusion
- After fixing the `CX3` scene-gating bug, the previously observed “strong positive branch on `CX3-C`” does **not** hold. That earlier conclusion is invalid and has been replaced by the corrected evidence in this file.
- `CX3-D` remains the strongest surviving positive branch. After a narrower conservative refinement (`low_bridge_scale`), it keeps public success unchanged, protects `parasol_misc`, improves same-alpha `Plain-Residual` by `+31.000` expansions on both public `exp3` and `exp4`, and reduces ordinary-scene overhead relative to the earlier accepted `CX3-D` draft.
- `CX3-C` remains useful only as an auxiliary hard-family signal reference: it still improves `flange`, but after the protected-regime fix it no longer beats same-alpha `Plain-Residual` on average and still regresses `parasol_misc` expansions.
- `CX3-A` and `CX3-B` are weaker: `CX3-A` regresses success and ordinary-scene cost, while `CX3-B` stays negative on average expansions.
- A targeted `CX3-D + aux-positive` follow-up was attempted using `CX3-C`-style local hard signals, but it was rejected because it materially increased `mp/csm` runtime and did not improve the public claim.
- Statistical reinforcement shows that the overall `+31` expansion gain is still weak at the 18-case public-bundle level (CI crosses zero), but the `parasol_misc` protection benefit is stronger and more stable (`reports/rs_p0cx3_stats_v1.md`).
- The honest current state is: `P0-CX` still does not achieve a decisive final advantage interval, but the best robust surviving branch is now the refined conservative `CX3-D` line.
- No expanded-hard result is used as evidence in this round; accepted evidence remains public `parasol_narrow` + `mp/csm` + same-alpha ablation under the corrected CUDA-capable environment.