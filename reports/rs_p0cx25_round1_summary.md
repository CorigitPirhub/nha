# P0-CX25 Round1 Summary

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; this round stayed public-first and did not consume hard-test evidence

## Variant Readout
- `CX25-B`: calib_val exp_delta=`1218.571`, calib_val overhead=`1.296792`, exp4 exp_delta=`392.889`, exp4 overhead=`1.359908`, flange exp_delta=`1428.400`
- `CX25-A`: calib_val exp_delta=`-331.571`, calib_val overhead=`2.688910`, exp4 exp_delta=`60.722`, exp4 overhead=`2.180158`, flange exp_delta=`224.800`
- `CX25-C`: calib_val exp_delta=`34.571`, calib_val overhead=`1.955348`, exp4 exp_delta=`61.444`, exp4 overhead=`1.718939`, flange exp_delta=`218.000`
- `CX25-D`: calib_val exp_delta=`1218.571`, calib_val overhead=`1.361072`, exp4 exp_delta=`392.889`, exp4 overhead=`1.431077`, flange exp_delta=`1428.400`
- `CX25-E`: calib_val exp_delta=`34.571`, calib_val overhead=`1.953874`, exp4 exp_delta=`61.444`, exp4 overhead=`1.734947`, flange exp_delta=`218.000`

## Ordering
- rank 1: `CX25-B`
- rank 2: `CX25-D`
- rank 3: `CX25-C`
- rank 4: `CX25-E`
- rank 5: `CX25-A`

## Readout
- `CX25-B` works as intended only as infrastructure: the diagnostic-to-operation compiler preserves `CX23-C`-level behavior while turning diagnostics into a reusable control-facing object, but it does not itself change policy outcomes.
- `CX25-A` shows that selective soft certificates, as currently implemented, are worse than plain `CCC`: they keep `maze = 0.0`, but still leave `parasol_misc = -66.667` and do not recover `flange`, so the selective trigger is not yet selective enough.
- `CX25-C` and `CX25-E` preserve the `maze` repair from `CCC` and keep `narrow_passage` positive, but they still leave `flange = +218.0` and `parasol_misc = -66.667`; calibrated review and group-stable objective have not yet reopened the lost head-family gain.
- `CX25-D` leaves the pattern essentially unchanged from `CX23-C`; the current tail soft downgrade does not materially affect `parasol_misc`.
- no `CX25` branch is promotable; accepted mainline remains `RS + refined CX3-D / RS-HPG`.
