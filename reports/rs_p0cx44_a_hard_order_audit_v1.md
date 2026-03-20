# CX44-A Hard Order Audit V1

- protocol: Latin-square hard order audit over `CX34-A (Full)`, `CX44-A (No-Witness-Transfer)`, and `CX44-A (Full)`
- hard root: `data/benchmark/rs_root_hard_v2_order_audit_subset_v1/test`
- num_cases: `14`
- inputs sha256: `outputs/rs_p0cx44_a_hard_order_audit_subset_v1/inputs_sha256.json`

## Overall vs `CX34-A (Full)`
- `CX44-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.008511`, prep_delta_ms=`0.002`, plan_delta_ms=`23.286`
- `CX44-A (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.009371`, prep_delta_ms=`0.002`, plan_delta_ms=`25.638`

## By Position vs `CX34-A (Full)`
- pos=`0` / `CX44-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.010996`, prep_delta_ms=`0.002`, plan_delta_ms=`30.109`
- pos=`0` / `CX44-A (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.003975`, prep_delta_ms=`0.001`, plan_delta_ms=`10.884`
- pos=`1` / `CX44-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.009940`, prep_delta_ms=`0.002`, plan_delta_ms=`27.135`
- pos=`1` / `CX44-A (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.014003`, prep_delta_ms=`0.004`, plan_delta_ms=`38.224`
- pos=`2` / `CX44-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.004604`, prep_delta_ms=`0.002`, plan_delta_ms=`12.614`
- pos=`2` / `CX44-A (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.010149`, prep_delta_ms=`0.002`, plan_delta_ms=`27.808`

## Absolute Order Readout
- `order_a` / pos=`0` / `CX34-A (Full)`: success_rate=`0.643`, avg_expansions=`4129.143`, avg_time_ms=`2738.364`
- `order_a` / pos=`1` / `CX44-A (No-Witness-Transfer)`: success_rate=`0.643`, avg_expansions=`4129.143`, avg_time_ms=`2768.153`
- `order_a` / pos=`2` / `CX44-A (Full)`: success_rate=`0.643`, avg_expansions=`4129.143`, avg_time_ms=`2752.771`
- `order_b` / pos=`0` / `CX44-A (No-Witness-Transfer)`: success_rate=`0.643`, avg_expansions=`4129.143`, avg_time_ms=`2749.250`
- `order_b` / pos=`1` / `CX44-A (Full)`: success_rate=`0.643`, avg_expansions=`4129.143`, avg_time_ms=`2757.062`
- `order_b` / pos=`2` / `CX34-A (Full)`: success_rate=`0.643`, avg_expansions=`4129.143`, avg_time_ms=`2740.155`
- `order_c` / pos=`0` / `CX44-A (Full)`: success_rate=`0.643`, avg_expansions=`4129.143`, avg_time_ms=`2768.475`
- `order_c` / pos=`1` / `CX34-A (Full)`: success_rate=`0.643`, avg_expansions=`4129.143`, avg_time_ms=`2729.926`
- `order_c` / pos=`2` / `CX44-A (No-Witness-Transfer)`: success_rate=`0.643`, avg_expansions=`4129.143`, avg_time_ms=`2767.964`