# Router Camera-Ready Repro Bundle (V2)

This bundle upgrades the Phase15 camera-ready package by including Step1~Step4 additions:
- Phase16 related-work baselines
- Phase17 offline policy == system policy
- Phase19 secondary quality metrics

## One-Command Reproduction
- `bash artifacts/router_camera_ready_v2/reproduce_main_tables_figures.sh`

## Container Reproduction
1. `docker build -t router-camera-ready-v2 -f artifacts/router_camera_ready_v2/Dockerfile .`
2. `docker run --rm -it router-camera-ready-v2`

## Outputs
- Audit JSON: `artifacts/router_camera_ready_v2/audit_summary.json`
- Manifest: `artifacts/router_camera_ready_v2/MANIFEST.sha256`
- Claim matrix: `artifacts/router_camera_ready_v2/claim_to_evidence.csv`
- Final bundle: `outputs/final_v2/manifest.json`
