# Step14 Trial Report (v1)

Protocol mapping: `docs/router_protocol_v1_current_mainline_note.md`
Selection semantics: all family comparison on `calib_train/calib_val`; `test` used only for the chosen family (if any).

## B1 — RCWS-B-Direct
- status: `val_screened`
- pooled calib_val ΔJ vs P5: `7.732269`
- calib_val head-to-head ΔJ (M/N/O): `{'M': -0.001469, 'N': -0.001816, 'O': 0.001618}`
- calib_val gate: `{'risk_ci95_upper_le_alpha_all_seeds': True, 'path_audit_hold_all_seeds': True, 'beats_M_on_val_mean': False, 'beats_N_on_val_mean': False, 'beats_O_on_val_mean': True, 'unique_arms': ['wa_w120', 'wa_w125', 'wa_w135'], 'dominant_arm_fraction_max': 0.9155124653739612, 'nonconstant_seed_count': 5, 'not_constantized': True}`

## Selection conclusion
- chosen family for test: `None`
- reason: All RCWS-B variants failed to beat M/N/O on calib_val or failed the non-degeneracy gate; no candidate was allowed to consume test.