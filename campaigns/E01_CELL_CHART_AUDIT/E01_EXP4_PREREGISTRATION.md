# E01-EXP-4 Preregistration — fresh-chart (s, T) audit on true rest-OCV data

Committed before the A123/INR archives are examined (they are pinned
but unopened; only filenames have been seen).

## Data

- A123 low-current OCV at 8 ambient temperatures (-10..50 C), pinned.
- INR 18650-20R incremental-current OCV, samples SP1/SP3 at 0/25/45 C.

## Chart, channels

Chart (s, T), chart point s0 = 0.5, T0 = 25 C; stencils from adjacent
SoC values on the OCV curve and adjacent temperature files. Channels
(all smooth functions on the chart, at most one s-blind):
  x1 = OCV(s, T)/V0, x2 = dOCV/ds /V0 (nondim), x3 = d2OCV/ds2 /V0,
  x4 = charge/discharge branch half-separation at (s, T)/V0
       (low-current hysteresis width). If the files carry only one
  branch, x4 falls back to OCV at a declared second SoC (s-blind,
  recorded), which retains a non-degenerate identity.
Cubic local fits supply derivatives (DD-3 lesson).

## Rungs and predictions (fixed now)

- EXP4-A single-chemistry chart audit (A123, six disjoint slots =
  six disjoint SoC/temperature estimation windows): prediction
  NOT_FALSIFIED at 5 sigma. Noise term: replicate spread across
  charge/discharge sweeps and, for INR, across SP1 vs SP2 samples.
- EXP4-B chemistry-mix falsification: slots alternately drawn from
  A123 (LFP) and INR (NMC-class) while claiming ONE chart: prediction
  FALSIFIED_MEASUREMENT_CONTRACT at |z| >= 5 (two fundamental
  relations cannot share a chart). This is the real-data teeth test.
- Statistics identical to E01: raw Pluecker residual, 300-draw SE,
  5 sigma, 2,000-draw bootstrap on rejection. Single set of
  predictions; results published as they fall; no re-tries.

## Claim boundary

Fresh-cell chart consistency only; no aging, SOH, or safety claim.
