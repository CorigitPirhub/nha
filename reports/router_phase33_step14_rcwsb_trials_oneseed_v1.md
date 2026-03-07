# Step14 Trial Report (v1)

Protocol mapping: `docs/router_protocol_v1_current_mainline_note.md`
Selection semantics: all family comparison on `calib_train/calib_val`; `test` used only for the chosen family (if any).

## B1 — RCWS-B-Direct
- status: `val_screened`
- pooled calib_val ΔJ vs P5: `6.664337`
- calib_val head-to-head ΔJ (M/N/O): `{'M': -0.001043, 'N': -0.001043, 'O': -0.001043}`
- calib_val gate: `{'risk_ci95_upper_le_alpha_all_seeds': True, 'path_audit_hold_all_seeds': True, 'beats_M_on_val_mean': False, 'beats_N_on_val_mean': False, 'beats_O_on_val_mean': False, 'unique_arms': ['wa_w125', 'wa_w135'], 'dominant_arm_fraction_max': 0.8518518518518519, 'nonconstant_seed_count': 1, 'not_constantized': False}`

## B2 — RCWS-B-Residual
- status: `val_screened`
- pooled calib_val ΔJ vs P5: `6.665381`
- calib_val head-to-head ΔJ (M/N/O): `{'M': 0.0, 'N': 0.0, 'O': 0.0}`
- calib_val gate: `{'risk_ci95_upper_le_alpha_all_seeds': True, 'path_audit_hold_all_seeds': True, 'beats_M_on_val_mean': True, 'beats_N_on_val_mean': True, 'beats_O_on_val_mean': True, 'unique_arms': ['wa_w125', 'wa_w135'], 'dominant_arm_fraction_max': 0.9876543209876543, 'nonconstant_seed_count': 0, 'not_constantized': False}`

## B3 — RCWS-B-Monotone
- status: `val_screened`
- pooled calib_val ΔJ vs P5: `6.665381`
- calib_val head-to-head ΔJ (M/N/O): `{'M': 0.0, 'N': 0.0, 'O': 0.0}`
- calib_val gate: `{'risk_ci95_upper_le_alpha_all_seeds': True, 'path_audit_hold_all_seeds': True, 'beats_M_on_val_mean': True, 'beats_N_on_val_mean': True, 'beats_O_on_val_mean': True, 'unique_arms': ['wa_w125', 'wa_w135'], 'dominant_arm_fraction_max': 0.9876543209876543, 'nonconstant_seed_count': 0, 'not_constantized': False}`

## Selection conclusion
- chosen family for test: `None`
- reason: All RCWS-B variants failed to beat M/N/O on calib_val or failed the non-degeneracy gate; no candidate was allowed to consume test.