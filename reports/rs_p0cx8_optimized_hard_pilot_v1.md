# P0-CX8 Optimized Hard Pilot V1

- scope: `calib_hard_v1` dev-only pilot; no test data used
- branch: `CX8-B / RS-KFM` only
- split root: `data/split/calib_hard_v1`
- train cases: `10`
- val cases: `7`
- cap: `20000`
- chosen params: `{'patch_radius': 5, 'hidden_dim': 96, 'gate_threshold': 0.42, 'hard_threshold': 0.78, 'useful_threshold': 0.38, 'hard_margin_m': 0.15, 'soft_margin_m': 0.4, 'soft_penalty': 0.45, 'learning_rate': 0.0008, 'weight_decay': 0.0001, 'epochs': 70, 'batch_size': 128}`
- train/val samples: `5190`/`4580`
- inputs sha256: `outputs/rs_p0cx8_optimized_hard_pilot_v1/inputs_sha256.json`

## Overall vs accepted `CX3-D` on calib_val
- success_delta_pp=`0.000`
- exp_delta=`-34.429`
- time_delta_ms=`-1036.843`
- mean_time_overhead_ratio=`0.727811`
- path_delta=`-0.053`

## Family Breakdown
- `flange`: success_delta_pp=`0.000`, exp_delta=`71.000`, time_overhead_ratio=`0.447151`
- `maze`: success_delta_pp=`0.000`, exp_delta=`-40.667`, time_overhead_ratio=`0.371089`
- `narrow_passage`: success_delta_pp=`0.000`, exp_delta=`-90.500`, time_overhead_ratio=`0.981332`
- `parasol_misc`: success_delta_pp=`0.000`, exp_delta=`-9.000`, time_overhead_ratio=`1.571592`

## Trial Trade-off
- best-expansion trial: `gate_threshold=0.42, hidden_dim=96` gives overall `exp_delta=-34.429`, but still has `mean_time_overhead_ratio=0.7278`.
- lowest-overhead trial: `gate_threshold=0.35, hidden_dim=64` reduces overhead to `0.2424`, but its overall `exp_delta` drops further to `-127.000`.

## Readout
- result: no positive cross-family pilot trend yet under the optimized implementation