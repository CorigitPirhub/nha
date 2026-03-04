# Dual-Path Router (Fast/Slow) — Camera-Ready Reproduction

This repository contains multiple research tracks. **For the top-tier (Top-Conf/Top-Journal) submission mainline, use the _dual-path router_ track.**

## What This Is

Given a planning query on a grid map, we **route** between:
- **Fast path**: low-latency planner settings.
- **Slow path**: higher-quality reference settings.

The router is evaluated under a **frozen protocol** with risk control:
- Protocol: `docs/router_protocol_v1.md`
- Primary metrics: `J` and violation probability `V` (see protocol)

## One-Command Reproduction (Recommended)

```bash
bash artifacts/router_camera_ready_v2/reproduce_main_tables_figures.sh
```

This reproduces the main tables/figures and rebuilds the **camera-ready V2** audit artifacts.

## Container Reproduction

```bash
docker build -t router-camera-ready-v2 -f artifacts/router_camera_ready_v2/Dockerfile .
docker run --rm -it router-camera-ready-v2
```

## Where To Look (Outputs)

- Final bundle manifest: `outputs/final_v2/manifest.json`
- Camera-ready audit: `artifacts/router_camera_ready_v2/audit_summary.json`
- Phase reports: `reports/`
- Paper assets: `paper/tables_router_v*/`, `paper/figures_router_v*/`

## Notes

- Step 3 (real-hardware longrun) is a **Top-Journal** requirement and is not required for **Top-Conf** readiness.

