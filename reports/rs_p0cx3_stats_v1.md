# P0-CX3 Statistical Reinforcement

- main variant: `cx3_d`
- auxiliary reference: `cx3_c`
- bootstrap_n: `50000`

## EXP3
- overall exp delta vs plain: `{'mean': 31.0, 'ci95_lo': -8.11111111111111, 'ci95_hi': 101.0, 'p_boot_le0': 0.23532}`
- overall time delta vs plain: `{'mean': 7.746253770569132, 'ci95_lo': -2.9102423718237937, 'ci95_hi': 23.93416725616488, 'p_boot_le0': 0.13564}`
- overall success delta vs plain: `{'mean': 0.0, 'ci95_lo': 0.0, 'ci95_hi': 0.0, 'p_boot_le0': 1.0}`
- parasol_misc exp delta vs plain: `{'mean': 104.0, 'ci95_lo': 0.16666666666666666, 'ci95_hi': 302.8333333333333, 'p_boot_le0': 0.01602}`
- narrow_passage exp delta vs plain: `{'mean': -16.5, 'ci95_lo': -49.5, 'ci95_hi': 0.0, 'p_boot_le0': 1.0}`
- flange exp delta vs plain: `{'mean': 0.0, 'ci95_lo': 0.0, 'ci95_hi': 0.0, 'p_boot_le0': 1.0}`

## EXP4
- overall exp delta vs plain: `{'mean': 31.0, 'ci95_lo': -8.11111111111111, 'ci95_hi': 101.0, 'p_boot_le0': 0.23532}`
- overall time delta vs plain: `{'mean': 2.689772524819192, 'ci95_lo': -9.079224756149213, 'ci95_hi': 19.78947201811631, 'p_boot_le0': 0.4083}`
- overall success delta vs plain: `{'mean': 0.0, 'ci95_lo': 0.0, 'ci95_hi': 0.0, 'p_boot_le0': 1.0}`
- parasol_misc exp delta vs plain: `{'mean': 104.0, 'ci95_lo': 0.16666666666666666, 'ci95_hi': 302.8333333333333, 'p_boot_le0': 0.01602}`
- narrow_passage exp delta vs plain: `{'mean': -16.5, 'ci95_lo': -49.5, 'ci95_hi': 0.0, 'p_boot_le0': 1.0}`
- flange exp delta vs plain: `{'mean': 0.0, 'ci95_lo': 0.0, 'ci95_hi': 0.0, 'p_boot_le0': 1.0}`

## Ordinary Support
- mp: `{'num_cases': 800, 'success_rate': 1.0, 'avg_expansions': 137.32125, 'avg_time_ms': 38.15187909480301}`
- csm: `{'num_cases': 400, 'success_rate': 1.0, 'avg_expansions': 349.4875, 'avg_time_ms': 61.13397352717584}`

## Reading
- A positive branch is only considered statistically reinforced if the paired expansion delta CI is mostly above zero or the bootstrap mass below zero is small.
- Subgroup evidence matters more than overall mean if the goal is specifically to protect `parasol_misc` while keeping hard-family gains.