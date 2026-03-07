# P0-C Round2 Fixed-Axis Report (V1)

- fixed cap (frozen from round1 dev selection): `3500`
- families: `['deadend_labyrinth', 'maze', 'narrow_passage']`
- no budget-cap search in this round; this is a fixed-protocol verification.

## dev::high_constraint_all
- num pairs: `19`
- success delta mean: `0.000000`; CI=`[0.0, 0.0]`; p<=0=`1.000000`
- expansion delta mean: `-19.210526`; CI=`[-48.16052631578947, 0.7368421052631579]`; p<=0=`0.966800`
- time delta mean: `-7.644788`; CI=`[-16.34746141238506, -0.0019918107060060827]`; p<=0=`0.975000`
- path delta mean: `0.006571`; CI=`[0.0, 0.01971327174140214]`; p<=0=`0.091000`

| scenario | n | success delta (pp) | exp delta (%) | time delta (%) |
|---|---:|---:|---:|---:|
| deadend_labyrinth | 6 | 0.000 | -1.287 | -1.969 |
| maze | 6 | 0.000 | 0.000 | -1.032 |
| narrow_passage | 7 | 0.000 | -0.908 | -0.764 |

## dev::public_anchor_only
- num pairs: `1`
- success delta mean: `0.000000`; CI=`[0.0, 0.0]`; p<=0=`1.000000`
- expansion delta mean: `0.000000`; CI=`[0.0, 0.0]`; p<=0=`1.000000`
- time delta mean: `-0.484082`; CI=`[-0.48408203292638063, -0.48408203292638063]`; p<=0=`1.000000`
- path delta mean: `nan`; CI=`[nan, nan]`; p<=0=`nan`

| scenario | n | success delta (pp) | exp delta (%) | time delta (%) |
|---|---:|---:|---:|---:|
| narrow_passage | 1 | 0.000 | 0.000 | -0.067 |

## test::high_constraint_all
- num pairs: `34`
- success delta mean: `0.000000`; CI=`[0.0, 0.0]`; p<=0=`1.000000`
- expansion delta mean: `-13.235294`; CI=`[-35.88308823529412, 2.264705882352941]`; p<=0=`0.891800`
- time delta mean: `-1.721351`; CI=`[-8.013342367399567, 3.8963334719643585]`; p<=0=`0.717200`
- path delta mean: `0.052854`; CI=`[0.0, 0.15856164350368118]`; p<=0=`0.360000`

| scenario | n | success delta (pp) | exp delta (%) | time delta (%) |
|---|---:|---:|---:|---:|
| deadend_labyrinth | 10 | 0.000 | -1.206 | -1.064 |
| maze | 11 | 0.000 | -0.003 | 0.651 |
| narrow_passage | 13 | 0.000 | -1.094 | -1.484 |

## test::public_anchor_only
- num pairs: `4`
- success delta mean: `0.000000`; CI=`[0.0, 0.0]`; p<=0=`1.000000`
- expansion delta mean: `-5.000000`; CI=`[-9.5, -0.5]`; p<=0=`1.000000`
- time delta mean: `0.581396`; CI=`[-1.0171555913984776, 2.1111348178237677]`; p<=0=`0.253600`
- path delta mean: `0.000000`; CI=`[0.0, 0.0]`; p<=0=`1.000000`

| scenario | n | success delta (pp) | exp delta (%) | time delta (%) |
|---|---:|---:|---:|---:|
| maze | 1 | 0.000 | -0.658 | 0.481 |
| narrow_passage | 3 | 0.000 | -0.310 | 0.163 |
