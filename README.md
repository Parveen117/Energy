# Energy

Certified energy-systems campaigns built on the recognition-kernel
response theorems: the rank-2 area-bracket theorem of
**Geometric Completion of Thermodynamic Response** (arXiv:2603.20773)
and the Cut-Square Response Decomposition Theorem
(Recognition-Kernel-Framework, `theorum/thermodynamics/10`), under the
audit discipline of
[Thermodynamics-Reproducibility](https://github.com/Parveen117/Thermodynamics-Reproducibility)
campaign T01 and
[Bio-tech](https://github.com/Parveen117/Bio-tech) campaigns B01/B02.

The programme direction is a certification layer for energy systems —
grid state, battery health, drilling navigation, generation forecasts —
where every verdict carries a checkable identity rather than a model's
opinion. Domains are entered one at a time, each behind its own
falsification ladder. Battery health is first because the certified
mathematics applies to it verbatim and public ground-truth datasets
exist for the experimental rung.

## First campaign — E01 Cell-Chart Audit (battery state of health)

A healthy cell at equilibrium is a set of smooth response surfaces on
the two-dimensional chart `(s, T)` — state of charge times
temperature. Four nondimensional channels mirror what a battery
management system already measures: open-circuit voltage, an
incremental-capacity proxy, internal-resistance ratio (Arrhenius in
T), and a thermal channel. On one chart, the six pairwise area
brackets must satisfy `P(B) = B12*B34 - B13*B24 + B14*B23 = 0`.

**Degradation is a hidden variable that is not a function of the
chart.** Capacity fade, resistance growth, and activation-energy shift
move the response surfaces themselves, so measurement slots taken
across a cell's life violate the single-chart identity beyond the
declared noise bound exactly when the cell has aged. The falsification
is the health signal.

### Completed rung ladder

| Rung | Design | Result |
| --- | --- | --- |
| E01A | six brackets from one shared gradient pair (algebraic control) | `PASS_CONTROL` |
| E01B | six disjoint slots, identical fresh cell | `NOT_FALSIFIED` (z = 0.0) |
| E01C | 2% voltage-sense gain fault | `NOT_FALSIFIED` (z = 0.0) — see honest boundary below |
| E01D | monotonic aging, 0.2% fade | `NOT_FALSIFIED` (z = +0.1) |
| E01D | monotonic aging, 10% fade (mid-life) | `NOT_FALSIFIED` (z = +4.9, below the 5-sigma threshold — reported as is) |
| E01D | monotonic aging, 20% fade (end of life) | `FALSIFIED_MEASUREMENT_CONTRACT` (z = +8.4; zero outside the 99.9% bootstrap interval) |
| E01E | cut-square localization | `PASS_CONTROL` — aged cell vs voltage-sensor fault separated |

Measurement contract: per-channel noise 1e-4 (nondimensional; ~0.4 mV
on voltage), 25 replicate averages per stencil node, SoC stencil 0.05,
temperature stencil 5 K, rejection at 5 sigma, 2,000-draw bootstrap for
every rejecting rung. Certificate: `results/E01_CERTIFICATE.json`
(pinned; CI regenerates and diffs it).

### Honest boundaries (theorem properties, stated openly)

- **Single-channel gain faults are Pluecker-invisible.** A gain error
  on one channel scales three brackets by the same factor; the
  Pfaffian scales and its zero is preserved exactly. E01C pins this as
  a regression test. Detection of that fault class comes from the
  cut-square rung, not the bracket audit.
- **The localization discriminant.** In the cut-square decomposition
  against the fresh-cell decoder, a pure voltage-sense gain fault puts
  ALL transverse energy in the channel-1 pairs (share = 1.000); cell
  aging spreads it across the resistance and thermal pairs (share
  ~0.5). "Is it the cell or the sensor?" gets a certified, localized
  answer — for a battery operator this is the difference between
  replacing a pack and recalibrating a BMS.
- **Mid-life is genuinely borderline.** At the declared contract,
  10% fade lands at z = +4.9 — under the threshold. That is reported
  as `NOT_FALSIFIED`, not rounded up. Sensitivity to earlier aging is
  a matter of tightening the measurement contract (lower noise, wider
  slots), which the certificate makes explicit rather than hiding.
- No state-of-health percentage, remaining-useful-life, or safety
  claim is made anywhere in this repository. The certified claim is
  chart-consistency verdicts under a declared measurement contract.

## Next rung — E01-EXP experimental (open)

Data contract declared before any data is fitted:

1. Public battery aging datasets providing OCV, capacity, and
   impedance versus cycle count over temperature — candidates: NASA
   Prognostics Center of Excellence battery dataset, Oxford battery
   degradation dataset, CALCE. Data is downloaded and pinned into
   `data/` with hashes before analysis.
2. Six disjoint slots drawn from distinct life stages of one cell (or
   distinct cells of one batch); one bracket per slot.
3. Declared per-channel uncertainty from the source; 5-sigma threshold
   fixed in advance; bootstrap audit for any rejection.
4. Outcomes reported whichever way they fall.

## Queued domains (not started, no claims)

Grid state certification (PMU voltage/frequency/phase charts),
directional-drilling sensor fusion (ATHENA's observability
decomposition underground), generation-forecast certificates. Each
enters only behind its own E-series falsification ladder.

## Reproduce

```bash
python -m pip install numpy pytest
python -m pytest tests -q
python campaigns/E01_CELL_CHART_AUDIT/run_e01.py
```
