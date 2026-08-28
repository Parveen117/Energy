# E01-EXP Preregistration

This document fixes every analysis choice for the experimental rung
BEFORE any dataset is downloaded or examined. It is committed first;
the data arrives second; the certificate reports whatever falls out.
Deviations from this document, if any become necessary, must be
recorded in the certificate under `protocol_deviations` with reasons.

## 1. Datasets (in order of preference)

1. **NASA Prognostics Center of Excellence battery dataset** — Li-ion
   18650 cells cycled to failure with impedance (EIS) measurements,
   groups at multiple ambient temperatures. Needed because the (s, T)
   chart requires a temperature axis.
2. **CALCE (University of Maryland) battery datasets** — as a second
   source if NASA's temperature coverage is insufficient.
3. Oxford battery degradation dataset — single-temperature (40 C);
   usable only for a reduced one-axis consistency check, NOT the full
   Pluecker rung. If only Oxford is available, the certificate must
   say the full rung was NOT executable and why.

On download, record each file's SHA-256 in `data/MANIFEST.sha256`
before analysis. Files are never edited.

## 2. Chart, channels, slots

- Chart point: s0 = 0.5 (50% SoC), T0 = the middle available ambient
  temperature; stencil = adjacent SoC points nearest +/-0.05 and the
  adjacent temperature groups.
- Channels per E01 core: OCV/V0 (rest voltage at s0 after >= 1 h
  relaxation or the dataset's rest points), incremental-capacity proxy
  from the OCV curve, internal resistance from EIS real-axis intercept
  (or DC pulse resistance if EIS absent) over R0 = fresh-cell value,
  thermal channel ln(T/298.15).
- Six disjoint slots = six distinct life stages of the same cell
  group, equally spaced in cycle count from fresh to the dataset's
  end-of-life definition (80% capacity). Each bracket uses only its
  own slot. Cell-to-cell spread within a temperature group at fixed
  life stage is measured first and entered into the noise term.

## 3. Statistics (identical to E01 synthetic rungs)

- Statistic: raw Pluecker residual P(B).
- Noise SE: 300 draws at the measured per-channel uncertainty
  (declared in the certificate from the data itself: replicate spread
  at fixed stage), replicate averaging as available in the data.
- Rejection threshold: 5 sigma, fixed here. Bootstrap (2,000 draws)
  for any rejection.
- Cut-square localization against the fresh-cell decoder, beta = 0.95,
  with the channel-1 pair-share discriminant, exactly as in E01E.

## 4. Predictions (falsifiable, made now)

- P1: slots drawn entirely from the first 5% of cycle life ->
  NOT_FALSIFIED.
- P2: slots spanning fresh to 80% capacity (end of life) ->
  FALSIFIED_MEASUREMENT_CONTRACT at |z| >= 5.
- P3: localization on end-of-life events -> channel-1 pair share
  below 0.9 (cell-side signature, not sensor-side).

If P2 fails (real aging does NOT falsify the chart at 5 sigma), that
result is published as-is: it would mean the measurement contract
achievable from this public data is too loose for the audit to serve
as a health signal at end-of-life contrast, and the certificate will
quantify the gap.

## 5. Claim boundary

No state-of-health percentage, remaining-useful-life, or safety claim.
The certified claim is chart-consistency verdicts under the recorded
measurement contract, on the named public datasets.
