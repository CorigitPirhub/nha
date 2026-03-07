# Step14 Trial Report (v1)

Protocol mapping: `docs/router_protocol_v1_current_mainline_note.md`
Selection semantics: all family comparison on `calib_train/calib_val`; `test` used only for the chosen family (if any).

## F2A — TARP-RRSV
- status: `val_screened`
- pooled calib_val ΔJ vs P5: `7.731366`
- calib_val head-to-head ΔJ (M/N/O): `{'M': -0.002164, 'N': -0.002529, 'O': 0.000906}`
- calib_val gate: `{'risk_ci95_upper_le_alpha_all_seeds': True, 'path_audit_hold_all_seeds': True, 'beats_M_on_val_mean': False, 'beats_N_on_val_mean': False, 'beats_O_on_val_mean': True, 'unique_arms': ['wa_w125', 'wa_w135'], 'dominant_arm_fraction_max': 1.0, 'nonconstant_seed_count': 0, 'not_constantized': False}`

## F2B — TARP-RRMIX
- status: `val_screened`
- pooled calib_val ΔJ vs P5: `7.731796`
- calib_val head-to-head ΔJ (M/N/O): `{'M': -0.001734, 'N': -0.002099, 'O': 0.001336}`
- calib_val gate: `{'risk_ci95_upper_le_alpha_all_seeds': True, 'path_audit_hold_all_seeds': True, 'beats_M_on_val_mean': False, 'beats_N_on_val_mean': False, 'beats_O_on_val_mean': True, 'unique_arms': ['wa_w125', 'wa_w135'], 'dominant_arm_fraction_max': 1.0, 'nonconstant_seed_count': 1, 'not_constantized': False}`

## F2C — TARP-RRGATE
- status: `val_screened`
- pooled calib_val ΔJ vs P5: `7.731366`
- calib_val head-to-head ΔJ (M/N/O): `{'M': -0.002164, 'N': -0.002529, 'O': 0.000906}`
- calib_val gate: `{'risk_ci95_upper_le_alpha_all_seeds': True, 'path_audit_hold_all_seeds': True, 'beats_M_on_val_mean': False, 'beats_N_on_val_mean': False, 'beats_O_on_val_mean': True, 'unique_arms': ['wa_w125', 'wa_w135'], 'dominant_arm_fraction_max': 1.0, 'nonconstant_seed_count': 0, 'not_constantized': False}`

## Selection conclusion
- chosen family for test: `None`
- reason: All TARP-line variants failed to beat M/N/O on calib_val or failed the TARP non-degeneracy gate; no candidate was allowed to consume test.