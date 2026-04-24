# Current Task Book

## Mainline

Only `RS + Macro Rescue / Subtype-Specific Macro Rescue` is active.

Router strict submission, Phase C/D/E, CX35+ follow-ups, and all self-built benchmark work are no longer active in this workspace.

## Retained Assets

- Code: `src/rs_macro_rescue`, containing the RS planner/inference stack and the folded Macro Rescue dependency stack.
- External datasets: `data/benchmark/csm`, `data/benchmark/mp`, `data/benchmark/parasol_narrow`.
- Entry point: `PYTHONPATH=src python -m rs_macro_rescue.cli.evaluate_external` or installed script `rs-macro-rescue-evaluate`.

## Removed Scope

- Self-built datasets: hard roots, calibration splits, router datasets, residual datasets, structrank datasets, replay datasets.
- Historical experiment outputs and reports.
- Router submission code and documents.
- Non-mainline CX branches and branch-specific runners.

## Immediate Status

The repository is intentionally reset to a lean RS + Macro Rescue base. All code now lives under `src/`; the old numbered experiment branches have been folded into `src/rs_macro_rescue/stack/`. Future work should start from this retained mainline and use only the preserved external datasets unless a new dataset is explicitly introduced.
