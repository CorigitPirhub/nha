# Router Phase17 Policy Alignment V1 Report

## Summary
- Runtime: `0.001 h`
- Router policy artifact: `artifacts/router_policy_v1`
- `policy.json` sha256: `ebc5d0433b0f65602dc6d7e07ddc98f9f7507a53fa5b8181088e2fe4c66afd39`

## Gate Check
- `policy_single_source_of_truth`: `True`
- `same_selected_cases_phase10`: `True`
- `same_selected_cases_phase12`: `True`
- `same_selected_cases_phase14`: `True`
- `phase10_12_14_gates_all_true_under_policy`: `True`
- `policy_vs_rule_no_regression_large`: `True`

## No-Regression Thresholds (Frozen)
- `min_success_delta_each` (policy - rule): `-0.0050`
- `max_p99_latency_delta_ms_each` (policy - rule): `+5.000`
- `min_worst10_success_delta` (policy - rule): `-0.0100`
- `min_recovery_success_delta` (policy - rule): `-0.0100`

## Key Deltas (policy - rule)
- `phase10/x86_rtx4090`: Δsuccess=`+0.0000`, Δp99_ms=`+0.880`, Δp95_ms=`+0.081`
- `phase10/jetson_orin`: Δsuccess=`+0.0000`, Δp99_ms=`+1.498`, Δp95_ms=`+0.132`
- `phase12/x86_rtx4090`: Δsuccess=`+0.0000`, Δp99_ms=`+0.899`, Δp95_ms=`+0.085`
- `phase12/jetson_orin`: Δsuccess=`+0.0000`, Δp99_ms=`+1.222`, Δp95_ms=`+0.121`

## Offline vs Deployment Note
This phase seals the paper-to-system gap by ensuring the closed-loop runner loads and logs a single policy artifact (`artifacts/router_policy_v1/`) with hash-tracked parameters and models. The offline risk certificates (Phase11/Theory v2) still apply only under the frozen counterfactual protocol; this phase explicitly reports any deployment-induced shifts via closed-loop metrics rather than assuming offline guarantees transfer unchanged.

## Artifacts
- `out_dir`: `outputs/router_phase17_policy_alignment_v1`
- `report_md`: `reports/router_phase17_policy_alignment_v1.md`
- `paper_table_csv`: `paper/tables_router_v5/table_phase17_policy_alignment.csv`
- `paper_fig_svg`: `paper/figures_router_v5/fig_policy_alignment_p99_latency.svg`
- `paper_fig_png`: `paper/figures_router_v5/fig_policy_alignment_p99_latency.png`
- `phase10_rule_stats`: `outputs/router_phase17_policy_alignment_v1/rule/phase10/stats.json`
- `phase10_policy_stats`: `outputs/router_phase17_policy_alignment_v1/policy/phase10/stats.json`
- `phase12_rule_stats`: `outputs/router_phase17_policy_alignment_v1/rule/phase12/stats.json`
- `phase12_policy_stats`: `outputs/router_phase17_policy_alignment_v1/policy/phase12/stats.json`
- `phase14_rule_stats`: `outputs/router_phase17_policy_alignment_v1/rule/phase14/stats.json`
- `phase14_policy_stats`: `outputs/router_phase17_policy_alignment_v1/policy/phase14/stats.json`
