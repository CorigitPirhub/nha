# RS Root Hard Benchmark Card (V1)

## Status
- type: internal standardized benchmark
- official/community benchmark: no
- intended role: RS-root hard-scene audit and development benchmark

## Motivation
- extend the tiny public `parasol_narrow` hard bundle into a larger, versioned hard benchmark
- support dev/test separation for root-claim development
- keep public anchors while adding synthetic hard families for broader geometry coverage

## Composition
- public anchor root: `data/benchmark/parasol_narrow/test`
- dev synthetic per family: `6`
- test synthetic per family: `10`
- families: `['bug_trap', 'alpha_puzzle', 'flange', 'narrow_passage', 'maze', 'deadend_labyrinth']`
- dev summary: `{'num_samples': 41, 'scenario_histogram': {'alpha_puzzle': 6, 'bug_trap': 6, 'deadend_labyrinth': 6, 'flange': 8, 'maze': 6, 'narrow_passage': 7, 'parasol_misc': 2}, 'difficulty_histogram': {'hard': 32, 'very_hard': 9}, 'source_histogram': {'parasol_public_anchor': 5, 'rs_root_hard_v2_synth': 36}, 'num_maps': 41}`
- test summary: `{'num_samples': 73, 'scenario_histogram': {'alpha_puzzle': 11, 'bug_trap': 11, 'deadend_labyrinth': 10, 'flange': 13, 'maze': 11, 'narrow_passage': 13, 'parasol_misc': 4}, 'difficulty_histogram': {'hard': 59, 'very_hard': 14}, 'source_histogram': {'parasol_public_anchor': 13, 'rs_root_hard_v2_synth': 60}, 'num_maps': 73}`

## Difficulty Relabeling
- source: `rs_root_structural_rule_v1`
- inputs: occupancy ratio, shortest-path stretch, clearance quantile, scenario-family prior
- labels: `hard`, `very_hard`
- note: this relabeling is internal and not inherited from any official source label

## Allowed Uses
- root-claim stress test and standardized internal benchmarking
- dev split for method shaping within the RS-root line
- test split for final internal reporting under the same benchmark version

## Forbidden Uses
- do not describe this benchmark as an official or community-standard benchmark
- do not mix this benchmark with training/calibration splits of unrelated later tasks
- do not hide the distinction between public-anchor samples and synthetic-extension samples

## Artifact Chain
- root: `data/benchmark/rs_root_hard_v2`
- meta: `data/benchmark/rs_root_hard_v2/meta.json`
- dev index: `data/benchmark/rs_root_hard_v2/dev_index.csv`
- test index: `data/benchmark/rs_root_hard_v2/test_index.csv`
- manifest: `outputs/rs_root_hard_benchmark_v2/manifest.json`
- audit report: `reports/rs_root_hard_benchmark_v2.md`