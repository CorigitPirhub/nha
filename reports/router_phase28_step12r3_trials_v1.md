# Step12-R3 Trial Report (v1)

Strict source root: `outputs/router_phase9_bench_v7_strict_alpha05_probeT_noleak/`
Execution order: `K -> I -> J -> L`
Re-run status: `completed on 2026-03-06; conclusions unchanged`

## Scheme K — DCDR
- pooled mean ΔJ: `-0.001423`
- pooled 95% CI: `[-0.002396, -0.000118]`
- bootstrap p(gt0): `0.981500`
- route-only mean ΔJ: `-0.001423`
- overhead mean: `0.000000`
- gate: `{'pooled_p_lt_0_01': False, 'pooled_ci95_not_cross_0': False, 'risk_ci95_upper_le_alpha_all_seeds': True}`

## Scheme I — CGAS
- pooled mean ΔJ: `-0.002891`
- pooled 95% CI: `[-0.004622, -0.001571]`
- bootstrap p(gt0): `1.000000`
- route-only mean ΔJ: `-0.002632`
- overhead mean: `0.000259`
- gate: `{'pooled_p_lt_0_01': False, 'pooled_ci95_not_cross_0': False, 'risk_ci95_upper_le_alpha_all_seeds': True}`

## Scheme J — CSRR
- stats: `{"scheme": "J", "name": "CSRR", "arm_points": {"always_fast": {"J_mean": 1.2204668167102941, "violation_rate": 0.305, "latency_ms": 0.7385711107053794}, "always_crop_padded": {"J_mean": 46.059810292635504, "violation_rate": 0.0125, "latency_ms": 321.24882464355323}, "always_slow": {"J_mean": 20.282779778744818, "violation_rate": 0.0, "latency_ms": 141.54774801660096}}, "mid_best_fraction": 0.005, "mid_beats_slow_fraction": 0.2325, "mid_beats_fast_fraction": 0.02, "dominated_by_best_single_arm": true, "status": "arm_pilot_only", "pilot_max_cases": 400}`

## Scheme L — CSSD
- pooled mean ΔJ: `-0.001307`
- pooled 95% CI: `[-0.002818, -0.000381]`
- bootstrap p(gt0): `1.000000`
- route-only mean ΔJ: `-0.001307`
- overhead mean: `0.000000`
- gate: `{'pooled_p_lt_0_01': False, 'pooled_ci95_not_cross_0': False, 'risk_ci95_upper_le_alpha_all_seeds': True}`
Overall conclusion: `K/I/L remain negative under strict pooled evaluation; J's first local arm is dominated, so Step12-R3 does not recover the strict main claim.`
