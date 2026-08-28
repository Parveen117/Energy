"""E01 core: Pluecker cell-chart audit for battery response channels.

Framework sources (consumed, not rederived)
-------------------------------------------
1. arXiv:2603.20773 rank-2 area-bracket theorem: any four smooth
   nondimensional response channels on a two-dimensional equilibrium
   chart give six pairwise area brackets with
   P(B) = B12*B34 - B13*B24 + B14*B23 = 0.
2. Recognition-Kernel-Framework theorum/thermodynamics/10 (T3.1/T4.1):
   exact cut-square decomposition of response energy against a
   declared decoder, in metric-whitened coordinates.
Audit discipline follows Thermodynamics-Reproducibility campaign T01
and Bio-tech campaigns B01/B02.

Battery chart
-------------
The two-dimensional chart is (s, T): state of charge and absolute
temperature. A healthy cell at equilibrium is described by smooth
response surfaces over this chart. The four nondimensional channels
mirror what a battery management system already measures:

  x1  open-circuit voltage, OCV(s, T) / V0
  x2  incremental-capacity proxy, s(1-s) * dOCV/ds / V0
  x3  internal-resistance ratio, R(s, T) / R0 (Arrhenius in T)
  x4  thermal channel, ln(T / 298.15)

x3's independent Arrhenius temperature dependence and the pure thermal
x4 keep the channel set chart-spanning (the B01 DD-2 lesson).

Why this is a health audit
--------------------------
Degradation (capacity fade, resistance growth) is a hidden variable
that is NOT a function of the (s, T) chart: it moves the response
surfaces themselves. Six disjoint measurement slots taken across a
cell's life therefore violate the single-chart Pluecker identity
beyond the declared noise bound exactly when the cell has aged; the
falsification IS the health signal. The cut-square localization then
separates cell-side aging from instrument-side sensor faults.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass

import numpy as np

REJECTION_SIGMA = 5.0
CHANNEL_NOISE = 1e-4          # per-channel nondimensional measurement noise
N_REPLICATE_AVG = 25          # declared replicate averaging per node
V0 = 3.7                      # V, nondimensionalization scale
R0 = 0.05                     # ohm, fresh-cell reference resistance
T_REF = 298.15                # K

PAIRS = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
PAIR_LABELS = ["12", "13", "14", "23", "24", "34"]


@dataclass(frozen=True)
class CellModel:
    """Smooth equilibrium cell response on the (s, T) chart.

    fade    : capacity fade fraction (aging; rescales usable SoC axis)
    r_grow  : resistance growth fraction (aging)
    Both aging parameters move the response surfaces; neither is a
    function of the chart, which is exactly what the audit detects.
    """

    fade: float = 0.0
    r_grow: float = 0.0
    Ea_over_k: float = 2500.0     # Arrhenius activation temperature, K
    alpha_T: float = 2.0e-4       # OCV thermal coefficient, V/K

    def ocv(self, s, T):
        s = np.asarray(s, dtype=float)
        T = np.asarray(T, dtype=float)
        se = np.clip(s / (1.0 - self.fade), 1e-4, 1 - 1e-4)
        return (3.0 + 0.9 * se + 0.12 * np.log(se / (1.0 - se))
                + self.alpha_T * (T - T_REF))

    def d_ocv_ds(self, s, T):
        s = np.asarray(s, dtype=float)
        se = np.clip(s / (1.0 - self.fade), 1e-4, 1 - 1e-4)
        dse = 1.0 / (1.0 - self.fade)
        return (0.9 + 0.12 / (se * (1.0 - se))) * dse

    def resistance(self, s, T):
        s = np.asarray(s, dtype=float)
        T = np.asarray(T, dtype=float)
        return (R0 * (1.0 + self.r_grow)
                * (1.0 + 0.3 * (1.0 - s) ** 2)
                * np.exp(self.Ea_over_k * (1.0 / T - 1.0 / T_REF)))


def channels(model: CellModel, s, T):
    """Four nondimensional chart-spanning response channels."""
    s_arr = np.asarray(s, dtype=float)
    T_arr = np.asarray(T, dtype=float)
    x1 = model.ocv(s_arr, T_arr) / V0
    x2 = s_arr * (1.0 - s_arr) * model.d_ocv_ds(s_arr, T_arr) / V0
    x3 = model.resistance(s_arr, T_arr) / R0
    x4 = np.log(T_arr / T_REF) + 0.0 * s_arr
    return np.stack([x1, x2, x3, x4], axis=0)


def gradients(channel_fn, s0, T0, ds, dT):
    u = (channel_fn(s0 + ds, T0) - channel_fn(s0 - ds, T0)) / (2.0 * ds)
    v = (channel_fn(s0, T0 + dT) - channel_fn(s0, T0 - dT)) / (2.0 * dT)
    return u, v


def brackets_common(u, v):
    return {f"B{i+1}{j+1}": u[i] * v[j] - u[j] * v[i] for i, j in PAIRS}


def independent_brackets(slot_fns, s0, T0, ds, dT):
    B = {}
    for (i, j), fn in zip(PAIRS, slot_fns):
        u, v = gradients(fn, s0, T0, ds, dT)
        B[f"B{i+1}{j+1}"] = u[i] * v[j] - u[j] * v[i]
    return B


def pluecker_residual(B):
    return B["B12"] * B["B34"] - B["B13"] * B["B24"] + B["B14"] * B["B23"]


def noise_standard_error(slot_fns, s0, T0, ds, dT, n_rep=300, seed=7):
    rng = np.random.default_rng(seed)
    eff = CHANNEL_NOISE / math.sqrt(N_REPLICATE_AVG)
    res = []
    for _ in range(n_rep):
        B = {}
        for (i, j), fn in zip(PAIRS, slot_fns):
            def noisy(s, T, fn=fn):
                x = fn(s, T)
                return x + rng.normal(0.0, eff, size=x.shape)
            u, v = gradients(noisy, s0, T0, ds, dT)
            B[f"B{i+1}{j+1}"] = u[i] * v[j] - u[j] * v[i]
        res.append(pluecker_residual(B))
    res = np.asarray(res)
    return float(np.mean(res)), float(np.std(res, ddof=1))


def verdict(z):
    return "NOT_FALSIFIED" if abs(z) < REJECTION_SIGMA \
        else "FALSIFIED_MEASUREMENT_CONTRACT"


# ---------------- cut-square localization (theorum/thermodynamics/10) ----

def metric_H():
    return np.diag(1.0 / (np.full(4, CHANNEL_NOISE) ** 2))


def response_event(model: CellModel, s0, T0, ds, dT, ws=1.0, wT=1.0):
    xp = channels(model, s0 + ds, T0)
    xm = channels(model, s0 - ds, T0)
    yp = channels(model, s0, T0 + dT)
    ym = channels(model, s0, T0 - dT)
    return ws * (xp - xm) / 2.0 + wT * (yp - ym) / 2.0


def declared_decoder(fresh: CellModel, s0, T0, ds, dT, beta=0.95):
    H = metric_H()
    c_raw = response_event(fresh, s0, T0, ds, dT)
    nrm = math.sqrt(float(c_raw @ H @ c_raw))
    return c_raw * (math.sqrt(beta) / nrm)


def cut_square_ledger(c, y):
    H = metric_H()
    Hs = np.sqrt(H)
    C, Y = Hs @ c, Hs @ y
    beta = float(C @ C)
    total = float(Y @ Y)
    L = float(C @ Y)
    captured = L * L
    reserve = (1.0 - beta) * total
    squares = {lbl: float((C[i] * Y[j] - C[j] * Y[i]) ** 2)
               for lbl, (i, j) in zip(PAIR_LABELS, PAIRS)}
    transverse = float(sum(squares.values()))
    return {
        "beta": beta,
        "captured_share": captured / total if total else 0.0,
        "transverse_share": transverse / total if total else 0.0,
        "dominant_pair": max(squares, key=squares.get),
        "pair_squares": squares,
        "identity_residual_T31_rel":
            (beta * total - captured - transverse) / max(beta * total, 1.0),
        "ledger_residual_T41_rel":
            (total - captured - reserve - transverse) / max(total, 1.0),
    }


def sha256_of(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()
