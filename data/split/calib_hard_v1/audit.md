# Calib Hard Split V1 Audit

- source benchmark: `data/benchmark/rs_root_hard_v2/dev`
- accepted baseline: `RS + refined CX3-D / RS-HPG`, cap=`20000`
- note: `cap=7000` partial screen is archived in `screen_rows_cap7000_partial.json`; under that stricter cap, `bug_trap` was already `0/6` success and the split was infeasible for hard-family coverage.
- total scanned dev cases (full 20000 scan): `41`
- successful accepted-baseline cases: `17`
- selected calib_train: `10`
- selected calib_val: `7`
- required families: `['narrow_passage', 'flange', 'maze', 'bug_trap', 'parasol_misc']`
- missing required families in success pool: `['bug_trap']`
- extra train-only families used to reach training scale: `['alpha_puzzle', 'deadend_labyrinth']`

## Family Audit
- `alpha_puzzle`: all=`6`, success=`1`, train=`1`, val=`0`
- `bug_trap`: all=`6`, success=`0`, train=`0`, val=`0`
- `deadend_labyrinth`: all=`6`, success=`5`, train=`5`, val=`0`
- `flange`: all=`8`, success=`1`, train=`0`, val=`1`
- `maze`: all=`6`, success=`4`, train=`1`, val=`3`
- `narrow_passage`: all=`7`, success=`4`, train=`2`, val=`2`
- `parasol_misc`: all=`2`, success=`2`, train=`1`, val=`1`

## Selected Train
- `sample_000024.npz` / `narrow_passage` / source=`rs_root_hard_v2_synth` / expansions=`3445.0` / time_ms=`824.3`
- `sample_000034.npz` / `maze` / source=`rs_root_hard_v2_synth` / expansions=`18982.0` / time_ms=`4926.3`
- `sample_000004.npz` / `parasol_misc` / source=`parasol_public_anchor` / expansions=`1152.0` / time_ms=`274.9`
- `sample_000025.npz` / `narrow_passage` / source=`rs_root_hard_v2_synth` / expansions=`624.0` / time_ms=`149.7`
- `sample_000012.npz` / `alpha_puzzle` / source=`rs_root_hard_v2_synth` / expansions=`19328.0` / time_ms=`4940.3`
- `sample_000035.npz` / `deadend_labyrinth` / source=`rs_root_hard_v2_synth` / expansions=`800.0` / time_ms=`204.3`
- `sample_000036.npz` / `deadend_labyrinth` / source=`rs_root_hard_v2_synth` / expansions=`6466.0` / time_ms=`1468.0`
- `sample_000038.npz` / `deadend_labyrinth` / source=`rs_root_hard_v2_synth` / expansions=`3429.0` / time_ms=`876.7`
- `sample_000039.npz` / `deadend_labyrinth` / source=`rs_root_hard_v2_synth` / expansions=`3935.0` / time_ms=`931.3`
- `sample_000040.npz` / `deadend_labyrinth` / source=`rs_root_hard_v2_synth` / expansions=`5306.0` / time_ms=`1340.2`

## Selected Val
- `sample_000026.npz` / `narrow_passage` / source=`rs_root_hard_v2_synth` / expansions=`3421.0` / time_ms=`829.6`
- `sample_000033.npz` / `maze` / source=`rs_root_hard_v2_synth` / expansions=`17061.0` / time_ms=`4430.1`
- `sample_000003.npz` / `parasol_misc` / source=`parasol_public_anchor` / expansions=`1006.0` / time_ms=`237.5`
- `sample_000030.npz` / `maze` / source=`rs_root_hard_v2_synth` / expansions=`14178.0` / time_ms=`3695.6`
- `sample_000032.npz` / `maze` / source=`rs_root_hard_v2_synth` / expansions=`12261.0` / time_ms=`3181.2`
- `sample_000027.npz` / `narrow_passage` / source=`rs_root_hard_v2_synth` / expansions=`2118.0` / time_ms=`547.0`
- `sample_000000.npz` / `flange` / source=`parasol_public_anchor` / expansions=`10673.0` / time_ms=`2528.4`