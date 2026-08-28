# E01-EXP-2 Preregistration — paired per-cell statistic

Committed BEFORE the statistic below is computed on any data. Honest
scope note: the underlying data (B0005/6/7/18, pinned in
`data/MANIFEST.sha256`) was already examined in E01-EXP-R, and the
per-stage transverse shares have been seen. What is being preregistered
is therefore the STATISTIC and its threshold, not data-blindness. The
statistic is chosen for exactness, not tuned to the observed values:
its null distribution is a finite permutation count with no free
parameters.

## Statistic

For each cell i, compute the transverse share T_i(k) of that cell's
own response event against the fresh-cell decoder, at the six life
stages k = 0..5 (identical pipeline to E01-EXP-R, deviations D1-D3
carried over).

- Per-cell monotonicity: cell i PASSES if T_i(k) is strictly
  increasing in k across all six stages (Kendall tau = 1).
- Under the null that stages are exchangeable for a cell (no aging
  signal), the probability of a strictly increasing arrangement is
  1/6! = 1/720 per cell.
- Joint criterion: ALL FOUR cells strictly increasing. Exact null
  probability (cells independent): (1/720)^4 ~ 3.7e-12.

## Decision rule (fixed now)

- PREDICTION EXP2-P: all four cells show strictly increasing
  T_i(k) across all six stages -> the aging trend is certified at
  exact permutation level p = (1/720)^4.
- If ANY cell breaks monotonicity at ANY transition, EXP2-P FAILS and
  the certificate reports which cell and which transition, with the
  values.

Descriptive (no thresholds): per-cell growth factors
T_i(5) / max(T_i(1), 1e-12) are reported as observed.

## Claim boundary

Unchanged from E01-EXP-R: no SOH percentage, no remaining-useful-life,
no safety claim. The certified claim is the exact-permutation aging
trend of the cut-square transverse share on the pinned public data.
