# Dual-Path Router (Fast/Slow) — Entry Point Moved

`README_router.md` is kept for backward compatibility.

The router entry point has been **merged into** `README.md` (see the section: “Dual-Path Router (Fast / Mid / Slow) — Camera-Ready (V2/V3)”).

## One-Command Reproduction

- **NeurIPS/ICML method-level bundle (V3):**
  ```bash
  bash artifacts/router_camera_ready_v3/reproduce_main_tables_figures.sh
  ```
- **Robotics/system bundle (V2):**
  ```bash
  bash artifacts/router_camera_ready_v2/reproduce_main_tables_figures.sh
  ```

## Outputs

- V3: `outputs/final_v3/manifest.json` + `artifacts/router_camera_ready_v3/audit_summary.json`
- V2: `outputs/final_v2/manifest.json` + `artifacts/router_camera_ready_v2/audit_summary.json`
