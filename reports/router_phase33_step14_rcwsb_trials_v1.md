# Step14 Trial Report (v1)

Protocol mapping: `docs/router_protocol_v1_current_mainline_note.md`
Selection semantics: all family comparison on `calib_train/calib_val`; `test` used only for the chosen family (if any).

## B1 — RCWS-B-Direct
- status: `val_screened`
- pooled calib_val ΔJ vs P5: `7.731932`
- calib_val head-to-head ΔJ (M/N/O): `{'M': -0.001807, 'N': -0.002153, 'O': 0.001281}`
- calib_val gate: `{'risk_ci95_upper_le_alpha_all_seeds': True, 'path_audit_hold_all_seeds': True, 'beats_M_on_val_mean': False, 'beats_N_on_val_mean': False, 'beats_O_on_val_mean': True, 'unique_arms': ['wa_w125', 'wa_w135'], 'dominant_arm_fraction_max': 0.853185595567867, 'nonconstant_seed_count': 5, 'not_constantized': False}`

## B2 — RCWS-B-Residual
- status: `val_screened`
- pooled calib_val ΔJ vs P5: `7.730477`
- calib_val head-to-head ΔJ (M/N/O): `{'M': -0.003261, 'N': -0.003607, 'O': -0.000173}`
- calib_val gate: `{'risk_ci95_upper_le_alpha_all_seeds': True, 'path_audit_hold_all_seeds': True, 'beats_M_on_val_mean': False, 'beats_N_on_val_mean': False, 'beats_O_on_val_mean': False, 'unique_arms': ['wa_w120', 'wa_w125', 'wa_w135'], 'dominant_arm_fraction_max': 0.9875346260387812, 'nonconstant_seed_count': 4, 'not_constantized': True}`

## B3 — RCWS-B-Monotone
- status: `val_screened`
- pooled calib_val ΔJ vs P5: `7.730480`
- calib_val head-to-head ΔJ (M/N/O): `{'M': -0.003258, 'N': -0.003604, 'O': -0.00017}`
- calib_val gate: `{'risk_ci95_upper_le_alpha_all_seeds': True, 'path_audit_hold_all_seeds': True, 'beats_M_on_val_mean': False, 'beats_N_on_val_mean': False, 'beats_O_on_val_mean': False, 'unique_arms': ['wa_w120', 'wa_w125', 'wa_w135'], 'dominant_arm_fraction_max': 0.9916897506925207, 'nonconstant_seed_count': 4, 'not_constantized': True}`

## Selection conclusion
- chosen family for test: `None`
- reason: All RCWS-B variants failed to beat M/N/O on calib_val or failed the non-degeneracy gate; no candidate was allowed to consume test.