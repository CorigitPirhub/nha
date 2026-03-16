# Calib Hard Split V1 Audit

- source benchmark: `data/benchmark/rs_root_hard_v2/dev`
- accepted baseline: `RS + refined CX3-D / RS-HPG`, cap=`20000`
- total scanned dev cases: `12`
- successful accepted-baseline cases: `6`
- selected calib_train: `0`
- selected calib_val: `6`
- required families: `['narrow_passage', 'flange', 'maze', 'bug_trap', 'parasol_misc']`
- missing required families in success pool: `['narrow_passage', 'flange', 'maze', 'bug_trap', 'parasol_misc']`

## Family Audit
- `alpha_puzzle`: all=`6`, success=`1`, train=`0`, val=`1`
- `deadend_labyrinth`: all=`6`, success=`5`, train=`0`, val=`5`

## Selected Train

## Selected Val
- `sample_000012.npz` / `alpha_puzzle` / source=`rs_root_hard_v2_synth` / expansions=`19328.0` / time_ms=`4940.3`
- `sample_000036.npz` / `deadend_labyrinth` / source=`rs_root_hard_v2_synth` / expansions=`6466.0` / time_ms=`1468.0`
- `sample_000040.npz` / `deadend_labyrinth` / source=`rs_root_hard_v2_synth` / expansions=`5306.0` / time_ms=`1340.2`
- `sample_000039.npz` / `deadend_labyrinth` / source=`rs_root_hard_v2_synth` / expansions=`3935.0` / time_ms=`931.3`
- `sample_000038.npz` / `deadend_labyrinth` / source=`rs_root_hard_v2_synth` / expansions=`3429.0` / time_ms=`876.7`
- `sample_000035.npz` / `deadend_labyrinth` / source=`rs_root_hard_v2_synth` / expansions=`800.0` / time_ms=`204.3`