# RS Root Hard Benchmark V2

Status: `built`

This benchmark upgrades `rs_root_hard_v1` toward a more standardized internal benchmark with `dev/test` separation, relabeled difficulty, split indices, and a benchmark card.

## Dev Split
- samples: `41`
- source histogram: `{'parasol_public_anchor': 5, 'rs_root_hard_v2_synth': 36}`
- scenario histogram: `{'alpha_puzzle': 6, 'bug_trap': 6, 'deadend_labyrinth': 6, 'flange': 8, 'maze': 6, 'narrow_passage': 7, 'parasol_misc': 2}`
- difficulty histogram: `{'hard': 32, 'very_hard': 9}`

## Test Split
- samples: `73`
- source histogram: `{'parasol_public_anchor': 13, 'rs_root_hard_v2_synth': 60}`
- scenario histogram: `{'alpha_puzzle': 11, 'bug_trap': 11, 'deadend_labyrinth': 10, 'flange': 13, 'maze': 11, 'narrow_passage': 13, 'parasol_misc': 4}`
- difficulty histogram: `{'hard': 59, 'very_hard': 14}`

## Standardization Notes
- public anchors are stratified into dev/test where possible; singleton public scenarios remain in test only.
- synthetic samples are generated separately for dev and test, with disjoint seeds and map ids.
- difficulty is relabeled by a structural rule using occupancy ratio, shortest-path stretch, clearance, and family prior.
- this benchmark is still internal/versioned, not an official community benchmark.