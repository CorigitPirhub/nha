# P0-CX6 Statistical Note

Status: `lightweight-bootstrap`
Date: `2026-03-09`

This note records a lightweight paired-bootstrap check for the most promising `CX6` candidate,
`CX6-D`, relative to the accepted baseline `CX3-D`.

## Pairing

Paired on the public `parasol_narrow` bundle, comparing:
- accepted `CX3-D`
- `CX6-D`

Budgets:
- `exp3`
- `exp4`

Bootstrap:
- `n = 50000`
- statistic: mean paired expansion delta `exp(CX3-D) - exp(CX6-D)`

## Results

- overall `exp3` delta  
  mean `+0.611`, 95% CI `[0.000, 1.778]`

- overall `exp4` delta  
  mean `+0.611`, 95% CI `[0.000, 1.778]`

- `parasol_misc` subgroup delta  
  mean `+1.833`, 95% CI `[0.000, 5.167]`

## Reading

These values suggest that `CX6-D` is directionally slightly better than accepted `CX3-D`,
but the gain is still too small to justify a mainline promotion.
