# CX43-D Release-Hit Diagnostics V1

- chosen json: `outputs/rs_p0cx43_d_pilot_v1/chosen.json`
- output root: `outputs/rs_p0cx43_d_release_diag_v1`
- inputs sha256: `outputs/rs_p0cx43_d_release_diag_v1/inputs_sha256.json`

## Public Aggregate
- total_release_hits=`0`
- total_fallback_full=`82823`
- total_singletons=`0`
- total_pregate_reject=`82823`

## Hard Aggregate
- total_release_hits=`0`
- total_fallback_full=`779671`
- total_singletons=`0`
- total_pregate_reject=`779671`

## Scenario Summary
- `hard` / `alpha_puzzle`: mean_release_hits=`0.000`, mean_release_full=`16277.545`, mean_singletons=`0.000`, mean_pregate_reject=`16277.545`, mean_release_ratio=`0.000000`, mean_time_ms=`10685.917`
- `hard` / `bug_trap`: mean_release_hits=`0.000`, mean_release_full=`14546.000`, mean_singletons=`0.000`, mean_pregate_reject=`14546.000`, mean_release_ratio=`0.000000`, mean_time_ms=`9746.188`
- `hard` / `deadend_labyrinth`: mean_release_hits=`0.000`, mean_release_full=`4379.100`, mean_singletons=`0.000`, mean_pregate_reject=`4379.100`, mean_release_ratio=`0.000000`, mean_time_ms=`2715.111`
- `hard` / `flange`: mean_release_hits=`0.000`, mean_release_full=`16005.923`, mean_singletons=`0.000`, mean_pregate_reject=`16005.923`, mean_release_ratio=`0.000000`, mean_time_ms=`10325.607`
- `hard` / `maze`: mean_release_hits=`0.000`, mean_release_full=`14593.727`, mean_singletons=`0.000`, mean_pregate_reject=`14593.727`, mean_release_ratio=`0.000000`, mean_time_ms=`9586.308`
- `hard` / `narrow_passage`: mean_release_hits=`0.000`, mean_release_full=`2098.308`, mean_singletons=`0.000`, mean_pregate_reject=`2098.308`, mean_release_ratio=`0.000000`, mean_time_ms=`1413.099`
- `hard` / `parasol_misc`: mean_release_hits=`0.000`, mean_release_full=`233.750`, mean_singletons=`0.000`, mean_pregate_reject=`233.750`, mean_release_ratio=`0.000000`, mean_time_ms=`169.793`
- `public` / `alpha_puzzle`: mean_release_hits=`0.000`, mean_release_full=`16.000`, mean_singletons=`0.000`, mean_pregate_reject=`16.000`, mean_release_ratio=`0.000000`, mean_time_ms=`11.575`
- `public` / `bug_trap`: mean_release_hits=`0.000`, mean_release_full=`6.000`, mean_singletons=`0.000`, mean_pregate_reject=`6.000`, mean_release_ratio=`0.000000`, mean_time_ms=`4.436`
- `public` / `flange`: mean_release_hits=`0.000`, mean_release_full=`10213.600`, mean_singletons=`0.000`, mean_pregate_reject=`10213.600`, mean_release_ratio=`0.000000`, mean_time_ms=`6402.156`
- `public` / `maze`: mean_release_hits=`0.000`, mean_release_full=`152.000`, mean_singletons=`0.000`, mean_pregate_reject=`152.000`, mean_release_ratio=`0.000000`, mean_time_ms=`99.076`
- `public` / `narrow_passage`: mean_release_hits=`0.000`, mean_release_full=`7150.500`, mean_singletons=`0.000`, mean_pregate_reject=`7150.500`, mean_release_ratio=`0.000000`, mean_time_ms=`4390.038`
- `public` / `parasol_misc`: mean_release_hits=`0.000`, mean_release_full=`496.500`, mean_singletons=`0.000`, mean_pregate_reject=`496.500`, mean_release_ratio=`0.000000`, mean_time_ms=`369.096`

## Public Runtime Delta vs `CX34-A`
- `sample_000017.npz` / `flange`: time_delta_ms=`79.663`, release_hits=`0`, fallback_full=`20000`, singletons=`0`, pregate_reject=`20000`
- `sample_000010.npz` / `narrow_passage`: time_delta_ms=`51.614`, release_hits=`0`, fallback_full=`20000`, singletons=`0`, pregate_reject=`20000`
- `sample_000015.npz` / `flange`: time_delta_ms=`47.776`, release_hits=`0`, fallback_full=`4833`, singletons=`0`, pregate_reject=`4833`
- `sample_000013.npz` / `flange`: time_delta_ms=`15.397`, release_hits=`0`, fallback_full=`3245`, singletons=`0`, pregate_reject=`3245`
- `sample_000005.npz` / `narrow_passage`: time_delta_ms=`8.564`, release_hits=`0`, fallback_full=`1680`, singletons=`0`, pregate_reject=`1680`
- `sample_000016.npz` / `flange`: time_delta_ms=`6.977`, release_hits=`0`, fallback_full=`2990`, singletons=`0`, pregate_reject=`2990`
- `sample_000006.npz` / `parasol_misc`: time_delta_ms=`3.291`, release_hits=`0`, fallback_full=`1025`, singletons=`0`, pregate_reject=`1025`
- `sample_000009.npz` / `narrow_passage`: time_delta_ms=`1.712`, release_hits=`0`, fallback_full=`565`, singletons=`0`, pregate_reject=`565`
- `sample_000007.npz` / `parasol_misc`: time_delta_ms=`0.963`, release_hits=`0`, fallback_full=`1019`, singletons=`0`, pregate_reject=`1019`
- `sample_000008.npz` / `parasol_misc`: time_delta_ms=`0.377`, release_hits=`0`, fallback_full=`282`, singletons=`0`, pregate_reject=`282`
- `sample_000003.npz` / `maze`: time_delta_ms=`0.189`, release_hits=`0`, fallback_full=`152`, singletons=`0`, pregate_reject=`152`
- `sample_000011.npz` / `alpha_puzzle`: time_delta_ms=`0.031`, release_hits=`0`, fallback_full=`16`, singletons=`0`, pregate_reject=`16`
- `sample_000012.npz` / `bug_trap`: time_delta_ms=`0.010`, release_hits=`0`, fallback_full=`6`, singletons=`0`, pregate_reject=`6`
- `sample_000014.npz` / `flange`: time_delta_ms=`0.004`, release_hits=`0`, fallback_full=`20000`, singletons=`0`, pregate_reject=`20000`
- `sample_000004.npz` / `parasol_misc`: time_delta_ms=`0.001`, release_hits=`0`, fallback_full=`0`, singletons=`0`, pregate_reject=`0`
- `sample_000000.npz` / `parasol_misc`: time_delta_ms=`-0.064`, release_hits=`0`, fallback_full=`411`, singletons=`0`, pregate_reject=`411`
- `sample_000001.npz` / `parasol_misc`: time_delta_ms=`-0.300`, release_hits=`0`, fallback_full=`242`, singletons=`0`, pregate_reject=`242`
- `sample_000002.npz` / `narrow_passage`: time_delta_ms=`-2.505`, release_hits=`0`, fallback_full=`6357`, singletons=`0`, pregate_reject=`6357`