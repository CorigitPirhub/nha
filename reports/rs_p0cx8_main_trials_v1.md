# P0-CX8 Focused Main Trials (strict pilot, not full-bundle)

- note: this round is a focused `parasol_misc` strict pilot used to validate the new CX8 successor-level infrastructure; it is **not** yet the final full-bundle verdict.
- strict selection split: `rs_root_hard_v2/dev -> calib_train/calib_val`
- calib_train cases: `1`
- calib_val cases: `1`
- public test cases: `2`
- hard_v2 test cases: `2`
- budgets evaluated: `['exp3']`
- inputs sha256: `outputs/rs_p0cx8_focused_misc_v1/inputs_sha256.json`

## Chosen Variants
- `CX8-A` params=`{'patch_radius': 5, 'hidden_dim': 96, 'prior_scale': 0.45, 'learning_rate': 0.001, 'weight_decay': 0.0001, 'epochs': 60, 'batch_size': 128}` val_delta=`{'success_delta_pp': 0.0, 'exp_delta': -5.0, 'time_delta_ms': -1038.7862788047642, 'path_delta': 0.2758284409852152}` train/val samples=`48`/`44`
- `CX8-B` params=`{'patch_radius': 5, 'hidden_dim': 96, 'hard_threshold': 0.72, 'useful_threshold': 0.42, 'hard_margin_m': 0.1, 'soft_margin_m': 0.35, 'soft_penalty': 0.3, 'learning_rate': 0.001, 'weight_decay': 0.0001, 'epochs': 70, 'batch_size': 128}` val_delta=`{'success_delta_pp': 0.0, 'exp_delta': 114.0, 'time_delta_ms': -8897.97719893977, 'path_delta': 0.0}` train/val samples=`480`/`440`
- `CX8-D` params=`{'patch_radius': 5, 'hidden_dim': 96, 'bottleneck_gate': 0.42, 'bundle_conf_thr': 0.5, 'bundle_scale': 0.4, 'learning_rate': 0.001, 'weight_decay': 0.0001, 'epochs': 60, 'batch_size': 128}` val_delta=`{'success_delta_pp': 0.0, 'exp_delta': 0.0, 'time_delta_ms': -23.011606885120273, 'path_delta': 0.0}` train/val samples=`21`/`27`
- `CX8-C` params=`{'patch_radius': 5, 'hidden_dim': 96, 'mode_conf_thr': 0.45, 'learning_rate': 0.001, 'weight_decay': 0.0001, 'epochs': 60, 'batch_size': 128}` val_delta=`{'success_delta_pp': 0.0, 'exp_delta': 0.0, 'time_delta_ms': -1212.05751481466, 'path_delta': 0.0}` train/val samples=`48`/`44`

## Final Test Summary vs Accepted `CX3-D`
- `public_parasol / exp3 / CX8-A`: success_delta_pp=`0.000`, exp_delta=`-27.000`, time_delta_ms=`-314.904`, path_delta=`-0.044`
- `public_parasol / exp3 / CX8-B`: success_delta_pp=`0.000`, exp_delta=`0.000`, time_delta_ms=`-2655.096`, path_delta=`0.000`
- `public_parasol / exp3 / CX8-C`: success_delta_pp=`0.000`, exp_delta=`0.000`, time_delta_ms=`-329.216`, path_delta=`0.000`
- `public_parasol / exp3 / CX8-D`: success_delta_pp=`0.000`, exp_delta=`0.000`, time_delta_ms=`-123.495`, path_delta=`0.000`
- `rs_root_hard_v2_test / exp3 / CX8-A`: success_delta_pp=`0.000`, exp_delta=`2.000`, time_delta_ms=`-303.321`, path_delta=`0.000`
- `rs_root_hard_v2_test / exp3 / CX8-B`: success_delta_pp=`0.000`, exp_delta=`0.000`, time_delta_ms=`-2876.686`, path_delta=`0.000`
- `rs_root_hard_v2_test / exp3 / CX8-C`: success_delta_pp=`0.000`, exp_delta=`0.000`, time_delta_ms=`-356.645`, path_delta=`0.000`
- `rs_root_hard_v2_test / exp3 / CX8-D`: success_delta_pp=`0.000`, exp_delta=`0.000`, time_delta_ms=`-93.555`, path_delta=`0.000`

## Verdict
- no `CX8` candidate establishes a decisive public strict advantage over accepted `CX3-D` in this round