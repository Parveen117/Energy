# Cross-repo audit (Energy vs Thermodynamics-Reproducibility T01, Bio-tech B01/B02)

Requested self-audit against the sibling repositories. Findings, with
diagnostics, exactly as they fell.

## Conventions — match

Bracket sign (u_i v_j - v_i u_j), pair order (12,13,14,23,24,34), and
Pfaffian P = b12 b34 - b13 b24 + b14 b23 are identical to
`thermo_recognition/plucker.py` in Thermodynamics-Reproducibility and
to Bio-tech B01. The E01A/B01A common-gradient controls match T01's
`common_gradient_control` semantics.

## AF-1 (minor) — EXP4 noise term deviated from its preregistration

The preregistration declared replicate spread (cell A vs cell B;
SP1 vs SP3) as the noise term; the implementation used cross-slot
gradient spread. Measured side by side they are numerically similar
(e.g. sigma_u3 0.30 vs 0.39), so no verdict direction changes, but the
deviation is recorded here rather than hidden.

## AF-2 (substantive) — EXP4 channels were not whitened; the audit's power collapsed

The theorem source consumed by B02
(Recognition-Kernel-Framework `theorum/thermodynamics/10`, Section 2)
requires metric whitening before any pairwise wedging of unlike-scale
coordinates. B02 obeyed this; EXP4 did not. The EXP4 channel scales
are disparate (curvature gradient ~0.3 vs ~1e-3 for the others), so
one channel dominates every slot's two-form, all slot forms become
nearly collinear, and the Pfaffian is mechanically small regardless of
chemistry. Diagnostics (T01 normalized residual |P|/||b||^2):
EXP4-A = 2.96e-04, EXP4-B chemistry mix = 1.83e-03 — the mix should be
O(1) for genuinely distinct charts. Consequence: **EXP4-A's
NOT_FALSIFIED is a LOW-POWER pass and EXP4-B's failure to falsify is
partly mechanical**, not only a noise-contract issue as first
interpreted. The published EXP4 certificate stands as the record of
its preregistration; this annotation corrects its interpretation.
Remedy: a NEW preregistration (EXP-5) with declared whitening — not a
silent rerun.

## AF-3 (checked, benign) — EXP3 metric floor was active on two channels

The capacity-ratio and resistance-ratio channels are ratios to each
cell's own fresh value, so their fresh-stage cross-cell spread is
exactly zero and the declared floor (1e-4) supplied their metric
weights — an arbitrary constant where a measured one was intended.
Robustness sweep of the full preregistered statistic under five
alternative declared metrics:

| metric | per-cell taus | combined p | verdict |
| --- | --- | --- | --- |
| floor 1e-4 (original) | 1.0, 0.87, 1.0, 1.0, 1.0, 1.0 | 3.1e-11 | PASS |
| floor 1e-3 | same | 3.1e-11 | PASS |
| floor 1e-2 | same | 3.1e-11 | PASS |
| stage-1 spread metric | all 1.0 | 6.5e-12 | PASS |
| equal weights | 1.0, 0.87, 1.0, ... | 3.1e-11 | PASS |

EXP3-P's CERTIFIED_AGING_TREND is metric-robust. Future metrics should
be estimated at a non-reference stage or from sweep replicates so the
floor never carries weight.
