# TrajectoryPlanning Distill

This workspace has been reduced to one line only:

`RS + Macro Rescue / Subtype-Specific Macro Rescue`

The retained data are the external benchmark datasets under:

- `data/benchmark/csm`
- `data/benchmark/mp`
- `data/benchmark/parasol_narrow`

Self-built datasets, router artifacts, historical experiment outputs, and non-mainline reports have been removed. The retained code is the RS planner stack plus the Macro Rescue dependency chain needed to build and evaluate the current mainline.

## Source Layout

- `src/rs_macro_rescue/mainline`: the RS-MacroRescue method, frozen parameters, and public API.
- `src/rs_macro_rescue/stack`: internal RS and Macro Rescue dependency stack folded out of the old numbered experiment branches.
- `src/rs_macro_rescue/env`, `planner`, `network`, `utils`: core planning and inference support.
- `src/rs_macro_rescue/cli`: runnable entry points.

## Entry Point

Run the external-dataset evaluator with an explicit neural heuristic checkpoint:

```bash
PYTHONPATH=src python -m rs_macro_rescue.cli.evaluate_external \
  --ours-checkpoint /path/to/checkpoint.pt \
  --device cpu
```

After installing the package in editable mode, the same entry point is available as `rs-macro-rescue-evaluate`.

The script rebuilds the RS-MacroRescue auxiliary memory from retained external training samples and evaluates `RS-MacroRescue` against the accepted `CX3-D` anchor on `parasol_narrow`, `mp`, and `csm`.
