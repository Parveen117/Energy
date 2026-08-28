# E01-EXP-5 Preregistration — whitened (s, T) chart audit (AF-2 remedy)

Committed after the cross-repo audit identified AF-2 and before any
whitened statistic is computed. Same data as EXP-4 (pinned), same two
rungs, one shot.

## Whitening (the only change from EXP-4)

Per the whitening contract of Recognition-Kernel-Framework
`theorum/thermodynamics/10` Section 2: each channel is divided by a
DECLARED scale before any bracket is formed. Declared scales = the
replicate (cell A vs cell B at 25 C, same window) standard deviation
of each channel's chart-point value, floored at 1e-6. Gradients,
brackets, and the Pfaffian are computed in these whitened coordinates.
Noise term = replicate gradient spread in whitened units (AF-1 remedy:
exactly the preregistered replicate construction).

## Rungs and predictions (fixed now)

- EXP5-A: A123 single-chemistry whitened chart -> NOT_FALSIFIED.
- EXP5-B: A123/INR chemistry mix on one claimed chart ->
  FALSIFIED_MEASUREMENT_CONTRACT at |z| >= 5, with the T01 normalized
  residual reported alongside.
- Statistics otherwise identical to E01. Results published as they
  fall; single shot; no re-tries on this data.
