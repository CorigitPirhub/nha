# P0-CX7 Statistical Note

Status: `lightweight-bootstrap`
Date: `2026-03-09`

This note records a lightweight paired-bootstrap check for the most promising `CX7` candidate,
`CX7-C`, relative to the accepted baseline `CX3-D`.

## Pairing

Paired on the public `parasol_narrow` bundle, comparing:
- accepted `CX3-D`
- `CX7-C`

Budgets:
- `exp3`
- `exp4`

Bootstrap:
- `n = 50000`
- statistic: mean paired expansion delta `exp(CX3-D) - exp(CX7-C)`

## Results

- overall `exp3` delta  
  mean `+5.889`, 95% CI `[-2.333, 19.611]`, `p_boot_le0 ≈ 0.231`

- overall `exp4` delta  
  mean `+5.889`, 95% CI `[-2.333, 19.611]`, `p_boot_le0 ≈ 0.231`

## Reading

These numbers suggest that `CX7-C` is directionally slightly better than accepted `CX3-D`,
but the gain is too small and statistically weak for mainline promotion.
