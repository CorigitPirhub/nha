# Router Camera-Ready Repro Bundle (V3)

This bundle extends V2 by adding NeurIPS/ICML method-level contributions (Step6~Step10):
- Phase21: method abstraction + minimal runnable demo
- Phase22: direct baselines (CDT/CRC-style) under the frozen protocol
- Phase23: K>=3 portfolio routing (multi-arm / multi-budget)
- Phase24: theory v3 with empirical inequality checks
- Phase25: cross-setting generalization (>=2 settings)

## One-Command Reproduction
- `bash artifacts/router_camera_ready_v3/reproduce_main_tables_figures.sh`

## Container Reproduction
1. `docker build -t router-camera-ready-v3 -f artifacts/router_camera_ready_v3/Dockerfile .`
2. `docker run --rm -it router-camera-ready-v3`

## Outputs
- Audit JSON: `artifacts/router_camera_ready_v3/audit_summary.json`
- Manifest: `artifacts/router_camera_ready_v3/MANIFEST.sha256`
- Claim matrix: `artifacts/router_camera_ready_v3/claim_to_evidence.csv`
- Final bundle: `outputs/final_v3/manifest.json`
