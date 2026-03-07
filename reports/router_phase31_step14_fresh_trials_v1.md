# Step14 Trial Report (v1)

Protocol mapping: `docs/router_protocol_v1_current_mainline_note.md`
Selection semantics: all family comparison on `calib_train/calib_val`; `test` used only for the chosen family (if any).

## E — CARL-WA
- status: `val_screened`
- pooled calib_val ΔJ vs P5: `6.817258`
- calib_val head-to-head ΔJ (M/N/O): `{'M': -0.915588, 'N': -0.915962, 'O': -0.91251}`
- calib_val gate: `{'risk_ci95_upper_le_alpha_all_seeds': False, 'path_audit_hold_all_seeds': True, 'beats_M_on_val_mean': False, 'beats_N_on_val_mean': False, 'beats_O_on_val_mean': False, 'unique_arms': ['fast'], 'dominant_arm_fraction_max': 1.0, 'not_constantized': False}`

## F — TARP-WA
- status: `val_screened`
- pooled calib_val ΔJ vs P5: `7.731156`
- calib_val head-to-head ΔJ (M/N/O): `{'M': -0.00169, 'N': -0.002065, 'O': 0.001387}`
- calib_val gate: `{'risk_ci95_upper_le_alpha_all_seeds': True, 'path_audit_hold_all_seeds': True, 'beats_M_on_val_mean': False, 'beats_N_on_val_mean': False, 'beats_O_on_val_mean': True, 'unique_arms': ['wa_w125', 'wa_w135'], 'dominant_arm_fraction_max': 1.0, 'not_constantized': False}`

## G — CPSF-WA
- status: `val_screened`
- pooled calib_val ΔJ vs P5: `5.695735`
- calib_val head-to-head ΔJ (M/N/O): `{'M': -2.037111, 'N': -2.037486, 'O': -2.034033}`
- calib_val gate: `{'risk_ci95_upper_le_alpha_all_seeds': False, 'path_audit_hold_all_seeds': True, 'beats_M_on_val_mean': False, 'beats_N_on_val_mean': False, 'beats_O_on_val_mean': False, 'unique_arms': ['cpsf_l020_q50_s030'], 'dominant_arm_fraction_max': 1.0, 'avg_field_std': 0.03038198048396029, 'not_trivial_field': True}`

## H — CETA-WA
- status: `val_screened`
- pooled calib_val ΔJ vs P5: `7.165221`
- calib_val head-to-head ΔJ (M/N/O): `{'M': -0.567625, 'N': -0.568, 'O': -0.564547}`
- calib_val gate: `{'risk_ci95_upper_le_alpha_all_seeds': False, 'path_audit_hold_all_seeds': True, 'beats_M_on_val_mean': False, 'beats_N_on_val_mean': False, 'beats_O_on_val_mean': False, 'unique_arms': ['ceta_a125_b120_c105_d55_p002'], 'dominant_arm_fraction_max': 1.0, 'avg_switch_rate': 0.1256271070855522, 'avg_state_diversity': 0.486426592797784, 'not_trivial_schedule': False}`

## Selection conclusion
- chosen family for test: `None`
- reason: E/F/G/H all failed to beat M/N/O on calib_val or violated the family-specific non-degeneracy gate; no candidate was allowed to consume test.