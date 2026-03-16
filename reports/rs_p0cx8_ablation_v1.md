# P0-CX8 Focused Ablation (strict pilot, calib_val only)

- note: this round is a focused `parasol_misc` strict pilot used to validate the new CX8 successor-level infrastructure; it is **not** yet the final full-bundle verdict.
- split used: `rs_root_hard_v2/dev -> calib_val` only
- calib_val cases: `1`

## Summary vs accepted `CX3-D`
- `CX8-A / learned`: success_delta_pp=`0.000`, exp_delta=`-5.000`, time_delta_ms=`-1077.579`
- `CX8-A / uniform`: success_delta_pp=`0.000`, exp_delta=`0.000`, time_delta_ms=`-2.267`
- `CX8-B / analytic_only`: success_delta_pp=`0.000`, exp_delta=`0.000`, time_delta_ms=`0.354`
- `CX8-B / learned`: success_delta_pp=`0.000`, exp_delta=`114.000`, time_delta_ms=`-8765.858`
- `CX8-B / soft_only`: success_delta_pp=`0.000`, exp_delta=`113.000`, time_delta_ms=`-8801.225`
- `CX8-C / baseline`: success_delta_pp=`0.000`, exp_delta=`0.000`, time_delta_ms=`0.001`
- `CX8-C / fixed_app`: success_delta_pp=`0.000`, exp_delta=`-5.000`, time_delta_ms=`-1045.922`
- `CX8-C / fixed_bca`: success_delta_pp=`0.000`, exp_delta=`0.000`, time_delta_ms=`-70.141`
- `CX8-C / fixed_kfm`: success_delta_pp=`0.000`, exp_delta=`114.000`, time_delta_ms=`-8772.732`
- `CX8-C / learned`: success_delta_pp=`0.000`, exp_delta=`0.000`, time_delta_ms=`-1212.093`
- `CX8-D / detector_only`: success_delta_pp=`0.000`, exp_delta=`0.000`, time_delta_ms=`0.233`
- `CX8-D / learned`: success_delta_pp=`0.000`, exp_delta=`0.000`, time_delta_ms=`-71.524`

- runtime_hours=`0.0094`