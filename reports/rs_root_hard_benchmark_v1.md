# RS Root Hard Benchmark V1

Status: `built`

This benchmark expands the previous tiny `parasol_narrow/test` hard bundle into a larger **test-only** benchmark for the RS-root claim.

## Composition
- public anchor root: `data/benchmark/parasol_narrow/test`
- synthetic families: `['bug_trap', 'alpha_puzzle', 'flange', 'narrow_passage', 'maze', 'deadend_labyrinth']`
- synthetic samples per family: `10`
- total test samples: `78`
- total maps: `77`
- source histogram: `{'public_anchor': 18, 'synthetic_hard': 60}`
- scenario histogram: `{'alpha_puzzle': 11, 'bug_trap': 11, 'deadend_labyrinth': 10, 'flange': 15, 'maze': 11, 'narrow_passage': 14, 'parasol_misc': 6}`
- difficulty histogram: `{'medium': 78}`

## Intended use
- Use this benchmark as the expanded high-difficulty benchmark for the RS-root claim.
- Keep it test-only; do not merge it into training or calibration splits of later method experiments.
- Report narrow/maze/deadend/other or the finer family histogram explicitly when writing root-claim evidence.

## Artifact chain
- output root: `data/benchmark/rs_root_hard_v1`
- meta: `data/benchmark/rs_root_hard_v1/meta.json`
- manifest: `outputs/rs_root_hard_benchmark_v1/manifest.json`