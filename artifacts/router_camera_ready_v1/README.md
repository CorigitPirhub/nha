# Router Camera-Ready Repro Bundle

## One-Command Reproduction
- `bash artifacts/router_camera_ready_v1/reproduce_main_tables_figures.sh`

## Container Reproduction
1. `docker build -t router-camera-ready -f artifacts/router_camera_ready_v1/Dockerfile .`
2. `docker run --rm -it router-camera-ready`

## Outputs
- Audit JSON: `artifacts/router_camera_ready_v1/audit_summary.json`
- Manifest: `artifacts/router_camera_ready_v1/MANIFEST.sha256`
- Claim matrix: `artifacts/router_camera_ready_v1/claim_to_evidence.csv`
