# P0-C RS Root Hard-Axis Attempt (V1)

This report records the first P0-C attempt to obtain a stronger nearest-baseline axis against `Hybrid A* (RS)`.

## Dev Selection
- benchmark: `rs_root_hard_v2:dev` stratified subset (`14` / `41` cases)
- selection rule: success delta first, then time reduction, then expansion reduction, with path delta <= 1% guard
- selected cap: `3500`
- dev success delta (pp): `0.000`
- dev expansions delta (%): `-5.542`
- dev time delta (%): `-4.828`
- dev path delta (%): `-0.446`

## Anchor-Only Test Once
- benchmark: `rs_root_hard_v2:test` with `source=parasol_public_anchor` only (`13` cases)
- cap: `3500`
- success delta (pp): `0.000`
- expansions delta (%): `2.960`
- time delta (%): `1.756`
- path delta (%): `0.000`

## Honest Conclusion
- This attempt did **not** establish a stronger nearest-baseline axis on the anchor-only test subset.
- The selected hard-budget cap looked promising on the stratified dev subset, but the gain did not transfer to the public-anchor test subset.
- Therefore P0-C remains open after this attempt.

- manifest: `outputs/rs_root_p0c_axis_v1/manifest.json`
- table: `paper/tables_rs_root_v1/table_rs_root_p0c_attempt_anchor_only.csv`