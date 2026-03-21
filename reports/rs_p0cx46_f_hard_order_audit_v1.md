# CX46-F Hard Order Audit V1

- protocol: Latin-square hard order audit over `CX34-A (Full)`, `CX46-F (No-Witness-Transfer)`, and `CX46-F (Full)`
- hard root: `data/benchmark/rs_root_hard_v2_order_audit_subset_v1/test`
- num_cases: `14`
- inputs sha256: `outputs/rs_p0cx46_f_hard_order_audit_v1/inputs_sha256.json`

## Overall vs `CX34-A (Full)`
- `CX46-F (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.006238`, prep_delta_ms=`0.014`, plan_delta_ms=`23.976`, witness_hit_delta=`64.000`
- `CX46-F (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.007808`, prep_delta_ms=`0.014`, plan_delta_ms=`30.015`, witness_hit_delta=`0.000`

## Overall vs `CX46-F (No-Witness-Transfer)`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.007748`, prep_delta_ms=`-0.014`, plan_delta_ms=`-30.015`, witness_hit_delta=`0.000`
- `CX46-F (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.001558`, prep_delta_ms=`-0.001`, plan_delta_ms=`-6.039`, witness_hit_delta=`64.000`

## Pairwise `CX46-F (Full)` vs `CX46-F (No-Witness-Transfer)`
- overall: mean_time_delta_ms=`-6.039`, mean_prep_delta_ms=`-0.001`, mean_plan_delta_ms=`-6.039`, win_rate_full=`0.524`, avg_witness_hits_full=`64.000`

## By Position vs `CX46-F (No-Witness-Transfer)`
- pos=`0` / `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.009729`, prep_delta_ms=`-0.011`, plan_delta_ms=`-37.748`, witness_hit_delta=`0.000`
- pos=`0` / `CX46-F (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.002594`, prep_delta_ms=`0.004`, plan_delta_ms=`-10.071`, witness_hit_delta=`64.000`
- pos=`1` / `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.010276`, prep_delta_ms=`-0.020`, plan_delta_ms=`-39.875`, witness_hit_delta=`0.000`
- pos=`1` / `CX46-F (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.003534`, prep_delta_ms=`-0.007`, plan_delta_ms=`-13.714`, witness_hit_delta=`64.000`
- pos=`2` / `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.003218`, prep_delta_ms=`-0.013`, plan_delta_ms=`-12.422`, witness_hit_delta=`0.000`
- pos=`2` / `CX46-F (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.001467`, prep_delta_ms=`0.002`, plan_delta_ms=`5.668`, witness_hit_delta=`64.000`

## Pairwise By Order
- `order_a`: mean_time_delta_ms=`-12.009`, mean_prep_delta_ms=`-0.005`, mean_plan_delta_ms=`-12.004`, win_rate_full=`0.571`, avg_witness_hits_full=`64.000`
- `order_b`: mean_time_delta_ms=`-12.285`, mean_prep_delta_ms=`0.001`, mean_plan_delta_ms=`-12.286`, win_rate_full=`0.643`, avg_witness_hits_full=`64.000`
- `order_c`: mean_time_delta_ms=`6.176`, mean_prep_delta_ms=`0.002`, mean_plan_delta_ms=`6.174`, win_rate_full=`0.357`, avg_witness_hits_full=`64.000`

## By Position vs `CX34-A (Full)`
- pos=`0` / `CX46-F (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.007205`, prep_delta_ms=`0.014`, plan_delta_ms=`27.677`, witness_hit_delta=`64.000`
- pos=`0` / `CX46-F (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.009825`, prep_delta_ms=`0.011`, plan_delta_ms=`37.748`, witness_hit_delta=`0.000`
- pos=`1` / `CX46-F (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.006812`, prep_delta_ms=`0.012`, plan_delta_ms=`26.161`, witness_hit_delta=`64.000`
- pos=`1` / `CX46-F (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.010383`, prep_delta_ms=`0.020`, plan_delta_ms=`39.875`, witness_hit_delta=`0.000`
- pos=`2` / `CX46-F (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.004700`, prep_delta_ms=`0.014`, plan_delta_ms=`18.091`, witness_hit_delta=`64.000`
- pos=`2` / `CX46-F (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.003228`, prep_delta_ms=`0.013`, plan_delta_ms=`12.422`, witness_hit_delta=`0.000`

## Absolute Order Readout
- `order_a` / pos=`0` / `CX34-A (Full)`: success_rate=`0.643`, avg_expansions=`4129.143`, avg_time_ms=`3843.143`, avg_witness_hits=`0.000`
- `order_a` / pos=`1` / `CX46-F (No-Witness-Transfer)`: success_rate=`0.643`, avg_expansions=`4129.143`, avg_time_ms=`3882.338`, avg_witness_hits=`0.000`
- `order_a` / pos=`2` / `CX46-F (Full)`: success_rate=`0.643`, avg_expansions=`4129.143`, avg_time_ms=`3870.328`, avg_witness_hits=`64.000`
- `order_b` / pos=`0` / `CX46-F (No-Witness-Transfer)`: success_rate=`0.643`, avg_expansions=`4129.143`, avg_time_ms=`3880.901`, avg_witness_hits=`0.000`
- `order_b` / pos=`1` / `CX46-F (Full)`: success_rate=`0.643`, avg_expansions=`4129.143`, avg_time_ms=`3868.616`, avg_witness_hits=`64.000`
- `order_b` / pos=`2` / `CX34-A (Full)`: success_rate=`0.643`, avg_expansions=`4129.143`, avg_time_ms=`3852.223`, avg_witness_hits=`0.000`
- `order_c` / pos=`0` / `CX46-F (Full)`: success_rate=`0.643`, avg_expansions=`4129.143`, avg_time_ms=`3870.834`, avg_witness_hits=`64.000`
- `order_c` / pos=`1` / `CX34-A (Full)`: success_rate=`0.643`, avg_expansions=`4129.143`, avg_time_ms=`3842.442`, avg_witness_hits=`0.000`
- `order_c` / pos=`2` / `CX46-F (No-Witness-Transfer)`: success_rate=`0.643`, avg_expansions=`4129.143`, avg_time_ms=`3864.658`, avg_witness_hits=`0.000`