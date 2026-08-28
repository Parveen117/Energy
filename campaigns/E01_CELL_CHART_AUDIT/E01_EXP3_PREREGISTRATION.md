# E01-EXP-3 Preregistration — new data, statistic designed for both known failure modes

Committed BEFORE the target data is downloaded or examined. Unlike
EXP-2, this preregistration is fully data-blind with respect to its
target datasets.

## Target data (none yet downloaded)

1. NASA PCoE Battery Aging ARC archives beyond the 24 C group —
   at least one additional ambient-temperature group (43 C or 4 C),
   raw .mat with discharge curves and EIS records
   (source: NASA PHM data repository / phm-datasets S3 bucket).
2. CALCE CS2 raw cycling files (web.calce.umd.edu), >= 6 cells.

On download: pin SHA-256 into data/MANIFEST.sha256 before analysis;
record source URLs in the certificate.

## Pipeline

Identical channel construction to E01-EXP-R (V@50% delivered
capacity / V0, nondimensional local slope, capacity ratio, resistance
ratio), deviations D1-D2 carried over where the dataset lacks rest OCV
or EIS (substitute DC pulse resistance, recorded as a deviation). If
two ambient-temperature groups are present, the FULL (s, T) Pluecker
rung of the original E01-EXP preregistration is executed first, with
its original statistics unchanged.

## Statistic for the aging trend (designed for the two observed failure modes)

Failure mode 1 (EXP-1): between-cell heterogeneity — cells age at
different rates, so between-cell spread normalization is underpowered.
Failure mode 2 (EXP-2): within-cell regeneration events — strict
monotonicity is brittle to real, documented capacity-recovery dips.

Preregistered statistic, fixed now:

- Per cell i with K >= 6 life stages, compute Kendall's tau_i between
  stage index and transverse share T_i(k).
- Per-cell exact permutation p_i = P(tau >= tau_i) under stage
  exchangeability (exact enumeration for K <= 8).
- Combine across N cells by Fisher's method:
  X = -2 * sum(ln p_i), referred to chi-square with 2N degrees of
  freedom.
- PREDICTION EXP3-P: combined p < 1e-6.

Rationale: tau tolerates isolated regeneration dips (tau = 0.87 for
one inversion in six stages) — failure mode 2; per-cell statistics
combined by Fisher use each cell as its own control — failure mode 1.
Both design choices are fixed here, before the data.

- Secondary descriptive outputs (no thresholds): per-stage transverse
  shares, growth factors, channel-1 pair shares (cell-vs-sensor
  discriminant), reported as observed.

## Stopping rule

One statistic, one threshold, committed here. If EXP3-P fails on the
new data, the result is published and no further statistic is tried on
that data.

## Claim boundary

Unchanged: no SOH percentage, no remaining-useful-life, no safety
claim.
