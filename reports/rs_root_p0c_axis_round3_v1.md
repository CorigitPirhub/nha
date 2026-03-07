# P0-C Round3 Expansion-Focused Search (V1)

- fixed cap: `3500`
- families: `['deadend_labyrinth', 'maze', 'narrow_passage']`
- search objective: no success drop, then maximize expansion gain on dev high-constraint-all; time is secondary; no budget-cap search in this round.

Chosen params: `{'fixed_cap': 3500, 'residual_alpha': 0.45, 'residual_corridor_suppress': 0.3, 'residual_open_boost': 0.45}`

## Dev Summary (chosen config)
- success delta mean: `0.000000`
- expansion delta mean: `-6.421053`; CI=`[-27.157895, 9.157895]`; p<=0=`0.732800`
- time delta mean: `-3.466698`; CI=`[-9.008998, 1.350962]`; p<=0=`0.914400`

## Test Summary (high_constraint_all)
- success delta mean: `0.000000`
- expansion delta mean: `-0.676471`; CI=`[-5.382353, 3.264706]`; p<=0=`0.622000`
- time delta mean: `-3.322671`; CI=`[-7.582740, 0.676004]`; p<=0=`0.949200`

## Test Summary (public_anchor_only)
- success delta mean: `0.000000`
- expansion delta mean: `-4.000000`; CI=`[-7.500000, -0.500000]`; p<=0=`1.000000`
- time delta mean: `2.988147`; CI=`[-3.265956, 13.215014]`; p<=0=`0.321400`

## Honest Conclusion
- Interpret the high-constraint-all test first; use public_anchor_only as a conservative sanity check.
- Third-round honest conclusion: the expansion-focused dev search did not uncover a parameter regime that reverses the sign of the expansion gap on the high-constraint test subset; the current RS-guided full model still does not establish a harder expansion axis over `Hybrid A* (RS)`.
- Paper-facing csv: `paper/tables_rs_root_v1/table_rs_root_p0c_round3_expansion_focus.csv`
