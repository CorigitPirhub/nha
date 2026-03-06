# Step14 Trial Report (v1)

Protocol mapping: `docs/router_protocol_v1_current_mainline_note.md`
Selection semantics: all family comparison on `calib_train/calib_val`; `test` used only for the chosen family (if any).

## A — RCWS-Q
- status: `val_screened`
- pooled calib_val ΔJ vs P5: `7.733326`
- calib_val head-to-head ΔJ (M/N/O): `{'M': -0.000208, 'N': -0.000577, 'O': 0.00288}`
- calib_val gate: `{'risk_ci95_upper_le_alpha_all_seeds': True, 'path_audit_hold_all_seeds': True, 'beats_M_on_val_mean': False, 'beats_N_on_val_mean': False, 'beats_O_on_val_mean': True, 'unique_arms': ['wa_w120', 'wa_w125', 'wa_w135'], 'dominant_arm_fraction_max': 0.8421052631578947, 'not_constantized': True}`

## B — PCSE
- status: `val_screened`
- pooled calib_val ΔJ vs P5: `6.817258`
- calib_val head-to-head ΔJ (M/N/O): `{'M': -0.916275, 'N': -0.916645, 'O': -0.913187}`
- calib_val gate: `{'risk_ci95_upper_le_alpha_all_seeds': False, 'path_audit_hold_all_seeds': True, 'beats_M_on_val_mean': False, 'beats_N_on_val_mean': False, 'beats_O_on_val_mean': False, 'unique_arms': ['fast'], 'dominant_arm_fraction_max': 1.0, 'not_constantized': False}`

## C — OMWD
- status: `val_screened`
- pooled calib_val ΔJ vs P5: `6.817258`
- calib_val head-to-head ΔJ (M/N/O): `{'M': -0.916275, 'N': -0.916645, 'O': -0.913187}`
- calib_val gate: `{'risk_ci95_upper_le_alpha_all_seeds': False, 'path_audit_hold_all_seeds': True, 'beats_M_on_val_mean': False, 'beats_N_on_val_mean': False, 'beats_O_on_val_mean': False, 'unique_arms': ['fast'], 'dominant_arm_fraction_max': 1.0, 'not_constantized': False}`

## D — SDAC-WA
- status: `val_screened`
- pooled calib_val ΔJ vs P5: `7.729825`
- calib_val head-to-head ΔJ (M/N/O): `{'M': -0.003708, 'N': -0.004078, 'O': -0.00062}`
- calib_val gate: `{'risk_ci95_upper_le_alpha_all_seeds': True, 'path_audit_hold_all_seeds': True, 'beats_M_on_val_mean': False, 'beats_N_on_val_mean': False, 'beats_O_on_val_mean': False, 'unique_arms': ['sdac_s125_l120_m048_p004', 'sdac_s135_l120_m048_p004'], 'dominant_arm_fraction_max': 1.0, 'avg_switch_rate': 0.034903047091412745, 'not_trivial_schedule': False}`

## Selection conclusion
- chosen family for test: `None`
- reason: A/B/C all failed to beat M/N/O on calib_val; D was also not strong enough to justify a one-shot test.