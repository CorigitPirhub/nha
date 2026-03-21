# CX46-J Hard Order Audit V1

- protocol: Latin-square hard order audit over `CX34-A (Full)`, `CX46-J (No-Witness-Transfer)`, `CX46-J (No-Credit-Gate)`, and `CX46-J (Full)`
- hard root: `data/benchmark/rs_root_hard_v2_order_audit_subset_v1/test`
- num_cases: `14`
- inputs sha256: `outputs/rs_p0cx46_j_hard_order_audit_v1/inputs_sha256.json`

## Overall vs `CX34-A (Full)`
- `CX46-J (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.027894`, prep_delta_ms=`0.013`, plan_delta_ms=`88.872`, witness_hit_delta=`63.857`, credit_skip_delta=`196.857`
- `CX46-J (No-Credit-Gate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.032374`, prep_delta_ms=`0.013`, plan_delta_ms=`103.149`, witness_hit_delta=`64.000`, credit_skip_delta=`0.000`
- `CX46-J (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.015474`, prep_delta_ms=`0.014`, plan_delta_ms=`49.295`, witness_hit_delta=`0.000`, credit_skip_delta=`0.000`

## Overall vs `CX46-J (No-Witness-Transfer)`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.015238`, prep_delta_ms=`-0.014`, plan_delta_ms=`-49.295`, witness_hit_delta=`0.000`, credit_skip_delta=`0.000`
- `CX46-J (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.012231`, prep_delta_ms=`-0.000`, plan_delta_ms=`39.577`, witness_hit_delta=`63.857`, credit_skip_delta=`196.857`
- `CX46-J (No-Credit-Gate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.016643`, prep_delta_ms=`-0.001`, plan_delta_ms=`53.854`, witness_hit_delta=`64.000`, credit_skip_delta=`0.000`

## Overall vs `CX46-J (No-Credit-Gate)`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.031359`, prep_delta_ms=`-0.013`, plan_delta_ms=`-103.149`, witness_hit_delta=`-64.000`, credit_skip_delta=`0.000`
- `CX46-J (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.004340`, prep_delta_ms=`0.001`, plan_delta_ms=`-14.277`, witness_hit_delta=`-0.143`, credit_skip_delta=`196.857`
- `CX46-J (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.016370`, prep_delta_ms=`0.001`, plan_delta_ms=`-53.854`, witness_hit_delta=`-64.000`, credit_skip_delta=`0.000`

## Absolute Order Readout
- `order_a` / pos=`0` / `CX34-A (Full)`: success_rate=`0.643`, avg_expansions=`4129.143`, avg_time_ms=`3034.082`, avg_witness_hits=`0.000`, avg_credit_gate_skips=`0.000`
- `order_a` / pos=`1` / `CX46-J (No-Witness-Transfer)`: success_rate=`0.643`, avg_expansions=`4129.143`, avg_time_ms=`3030.489`, avg_witness_hits=`0.000`, avg_credit_gate_skips=`0.000`
- `order_a` / pos=`2` / `CX46-J (No-Credit-Gate)`: success_rate=`0.643`, avg_expansions=`4129.143`, avg_time_ms=`3020.963`, avg_witness_hits=`64.000`, avg_credit_gate_skips=`0.000`
- `order_a` / pos=`3` / `CX46-J (Full)`: success_rate=`0.643`, avg_expansions=`4129.143`, avg_time_ms=`3018.826`, avg_witness_hits=`63.857`, avg_credit_gate_skips=`196.857`
- `order_b` / pos=`0` / `CX46-J (No-Witness-Transfer)`: success_rate=`0.643`, avg_expansions=`4129.143`, avg_time_ms=`3324.509`, avg_witness_hits=`0.000`, avg_credit_gate_skips=`0.000`
- `order_b` / pos=`1` / `CX46-J (No-Credit-Gate)`: success_rate=`0.643`, avg_expansions=`4129.143`, avg_time_ms=`3412.045`, avg_witness_hits=`64.000`, avg_credit_gate_skips=`0.000`
- `order_b` / pos=`2` / `CX46-J (Full)`: success_rate=`0.643`, avg_expansions=`4129.143`, avg_time_ms=`3408.841`, avg_witness_hits=`63.857`, avg_credit_gate_skips=`196.857`
- `order_b` / pos=`3` / `CX34-A (Full)`: success_rate=`0.643`, avg_expansions=`4129.143`, avg_time_ms=`3389.817`, avg_witness_hits=`0.000`, avg_credit_gate_skips=`0.000`
- `order_c` / pos=`0` / `CX46-J (No-Credit-Gate)`: success_rate=`0.643`, avg_expansions=`4129.143`, avg_time_ms=`3412.593`, avg_witness_hits=`64.000`, avg_credit_gate_skips=`0.000`
- `order_c` / pos=`1` / `CX46-J (Full)`: success_rate=`0.643`, avg_expansions=`4129.143`, avg_time_ms=`3249.515`, avg_witness_hits=`63.857`, avg_credit_gate_skips=`196.857`
- `order_c` / pos=`2` / `CX34-A (Full)`: success_rate=`0.643`, avg_expansions=`4129.143`, avg_time_ms=`2987.367`, avg_witness_hits=`0.000`, avg_credit_gate_skips=`0.000`
- `order_c` / pos=`3` / `CX46-J (No-Witness-Transfer)`: success_rate=`0.643`, avg_expansions=`4129.143`, avg_time_ms=`3281.483`, avg_witness_hits=`0.000`, avg_credit_gate_skips=`0.000`
- `order_d` / pos=`0` / `CX46-J (Full)`: success_rate=`0.643`, avg_expansions=`4129.143`, avg_time_ms=`3424.434`, avg_witness_hits=`63.857`, avg_credit_gate_skips=`196.857`
- `order_d` / pos=`1` / `CX34-A (Full)`: success_rate=`0.643`, avg_expansions=`4129.143`, avg_time_ms=`3334.810`, avg_witness_hits=`0.000`, avg_credit_gate_skips=`0.000`
- `order_d` / pos=`2` / `CX46-J (No-Witness-Transfer)`: success_rate=`0.643`, avg_expansions=`4129.143`, avg_time_ms=`3306.830`, avg_witness_hits=`0.000`, avg_credit_gate_skips=`0.000`
- `order_d` / pos=`3` / `CX46-J (No-Credit-Gate)`: success_rate=`0.643`, avg_expansions=`4129.143`, avg_time_ms=`3313.121`, avg_witness_hits=`64.000`, avg_credit_gate_skips=`0.000`