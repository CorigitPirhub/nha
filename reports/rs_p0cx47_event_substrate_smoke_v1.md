# CX47 Event Substrate Smoke V1

- protocol: lightweight event logging / replay substrate smoke on `CX46-F`, using fixed public samples only; infrastructure validation only, not a new algorithm branch
- extractor: `scripts/extract_cx47_event_logs_v1.py`
- substrate: `rs_cx47/event_substrate.py`

## Validated Capabilities
- wraps an existing successor policy without modifying planner core semantics
- logs macro-bearing review events at `extra_successors / rank_successors`
- records:
  - structural identifiers: `scenario / class_key / must_precede / macro_count`
  - search context: `popped / x / y / yaw / anchor`
  - event outcomes: `full_review / witness_hit / store_negative`
  - cheap auxiliary features: `support_count / store_strength_proxy / event_seen`
- exports per-event CSV and per-case CSV

## Smoke Output
- case table: `outputs/cx47_event_logs_v1/cx46f_cases.csv`
- event table: `outputs/cx47_event_logs_v1/cx46f_events.csv`

## Smoke Readout
- `sample_000000.npz / parasol_misc`:
  - `witness_hits = 271`
  - `witness_store_negative = 115`
  - `witness_full_reviews = 116`
  - `num_events = 387`
- `sample_000001.npz / parasol_misc`:
  - `witness_hits = 190`
  - `witness_store_negative = 48`
  - `witness_full_reviews = 49`
  - `num_events = 239`

## Interpretation
- the substrate is now able to expose event-level rows for the current accepted runtime candidate without changing search semantics
- this removes the previous bottleneck where every new `CX47-*` branch needed ad hoc heavy trace machinery before event-level analysis was possible
- subsequent `CX47` branches should reuse this substrate rather than building branch-specific diagnostics
