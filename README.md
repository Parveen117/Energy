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

## E01-EXP-R — executed on real NASA PCoE cells (results as they fell)

Data: the four 24 C cells (B0005/6/7/18) from a community GitHub mirror
of the NASA PCoE set, hashes pinned in `data/MANIFEST.sha256`
(deviation D3: authenticity rests on the mirror). The full (s, T)
Pluecker rung was **NOT_EXECUTABLE** — only one ambient-temperature
group is publicly mirrored on an allowed source — and the certificate
says so. The preregistered reduced path (cut-square decomposition of
life-stage response events against the fresh-cell decoder) was
executed with deviations D1–D3 recorded.

Transverse share of real response energy that the fresh-cell decoder
cannot capture, by life stage (capacity ratio in brackets):

| Stage | Capacity | Transverse share |
| --- | --- | --- |
| fresh | 1.000 | ~0 |
| 1 | 0.946 | 4.6e-3 |
| 2 | 0.853 | 2.0e-2 |
| 3 | 0.777 | 4.6e-2 |
| 4 | 0.740 | 5.9e-2 |
| 5 (EOL) | 0.694 | 7.6e-2 |

Monotonic growth across all six stages — the aging signal is real.
Preregistered predictions, exactly as they fell:

- **P1 pass**: fresh events carry ~zero transverse share.
- **P2 FAIL** (z = 1.6, needed 5): with only four cells that age at
  visibly different rates, the between-cell spread is too wide for the
  preregistered spread-normalized statistic, even thougheach cell's
  own transverse share rises ~15x over life. The gap is quantified in
  the certificate; a per-cell paired statistic is the natural
  preregistration for E01-EXP-2, and it will be committed BEFORE any
  new data, not retrofitted to this run.
- **P3 pass** (channel-1 pair share 0.0015 << 0.9): on real cells the
  aging signature sits decisively in the capacity/resistance pairs,
  not the voltage pairs — the cell-vs-sensor discriminant behaves on
  real data exactly as the synthetic rung predicted.

Certificate: `results/E01_EXP_REDUCED_CERTIFICATE.json` (pinned).

## E01-EXP-2 — preregistered exact statistic (results as they fell)

Statistic committed before computation (`E01_EXP2_PREREGISTRATION.md`):
all four cells must show strictly increasing transverse share across
all six life stages (Kendall tau = 1; exact joint null probability
(1/720)^4).

**EXP2-P FAILED.** B0005 breaks monotonicity at transitions 3->4 and
4->5 (0.0555 -> 0.0464 -> 0.0444); B0006, B0007, B0018 are strictly
monotonic with growth factors x22, x9, x931. Interpretation (labeled
as such, not an excuse): B0005's late-life dip is consistent with the
well-documented rest-induced capacity-regeneration events in the NASA
cells — real electrochemistry that a strict-monotonicity statistic is
brittle to. Certificate: `results/E01_EXP2_CERTIFICATE.json`.

**Stopping rule, stated now:** two preregistered statistics have been
tried on this dataset and both failed for identifiable reasons
(between-cell heterogeneity; within-cell regeneration). Further
statistic iterations on THIS dataset stop here — a third attempt would
be threshold-shopping. The next preregistration targets NEW data (a
second temperature group or CALCE cells) with a statistic designed for
both known failure modes, committed before that data is touched. The
plainly visible underlying signal — transverse share growing an order
of magnitude or more over life in every cell — remains descriptive,
not certified, until it passes a preregistered test on fresh data.

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
