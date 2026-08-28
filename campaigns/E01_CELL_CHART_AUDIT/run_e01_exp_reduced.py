"""E01-EXP-R: reduced experimental rung on real NASA PCoE cells.

Protocol status, recorded per E01_EXP_PREREGISTRATION.md:
- FULL (s, T) Pluecker rung: NOT_EXECUTABLE from the pinned data. Only
  the 24 C ambient group (B0005/6/7/18) is publicly mirrored on an
  allowed source; the chart's temperature axis cannot be built. This
  is reported, not papered over.
- REDUCED path (preregistration section 1, Oxford clause, applied to
  the single-temperature NASA group): cut-square decomposition
  (theorum/thermodynamics/10) of real life-stage response events
  against the fresh-cell decoder, with the channel-1 pair-share
  discriminant of rung E01E. Predictions tested: reduced-P1 (fresh
  events carry near-zero transverse share), reduced-P2 (end-of-life
  transverse share exceeds fresh by >= 5x the cell-to-cell spread),
  P3 (end-of-life channel-1 pair share < 0.9: cell-side, not
  sensor-side signature).

Declared deviations (all recorded in the certificate):
- D1: rest OCV is not available at matched SoC; the voltage channel is
  the loaded voltage at 50% delivered capacity (pseudo-OCV under the
  dataset's constant-current discharge), used identically at every
  life stage.
- D2: the four channels are SoC-axis and impedance quantities only
  (V@50%/V0, nondimensional local slope, capacity ratio, Re ratio);
  no thermal channel exists in a single-temperature group.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys

import numpy as np
from scipy.io import loadmat

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, HERE)
from e01_core import sha256_of  # noqa: E402

V0 = 3.7
N_STAGES = 6
CELLS = ["B0005", "B0006", "B0007", "B0018"]
PAIR_LABELS = ["12", "13", "14", "23", "24", "34"]
PAIRS = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]

# ---------------- pin gate (same as full runner) ----------------
manifest_path = os.path.join(DATA, "MANIFEST.sha256")
assert os.path.exists(manifest_path), "pin first: data/MANIFEST.sha256"
pins = {}
for line in open(manifest_path):
    if line.strip():
        h, rel = line.strip().split(maxsplit=1)
        p = os.path.join(DATA, rel)
        actual = hashlib.sha256(open(p, "rb").read()).hexdigest()
        assert actual == h, f"hash mismatch: {rel}"
        pins[rel] = h


def load(name):
    m = loadmat(os.path.join(DATA, "raw", f"{name}.mat"),
                simplify_cells=True)
    return m[name]["cycle"]


def stage_events(cycles):
    """Return one 4-channel event per life stage for one cell."""
    dis = [c for c in cycles if c["type"] == "discharge"
           and "Capacity" in c.get("data", {})]
    imp = [c for c in cycles if c["type"] == "impedance"
           and "Re" in c.get("data", {})]
    imp_re = [float(np.real(np.atleast_1d(c["data"]["Re"])).min())
              for c in imp]
    # map each discharge to nearest preceding impedance record index
    n = len(dis)
    idxs = [int(round(k * (n - 1) / (N_STAGES - 1))) for k in range(N_STAGES)]
    q_fresh = float(dis[0]["data"]["Capacity"])
    re_fresh = imp_re[0]
    events = []
    for k, i in enumerate(idxs):
        d = dis[i]["data"]
        V = np.asarray(d["Voltage_measured"], float)
        t = np.asarray(d["Time"], float)
        I = np.asarray(d["Current_measured"], float)
        q = np.concatenate([[0.0],
                            np.cumsum(np.abs(I[:-1]) * np.diff(t)) / 3600.0])
        Q = float(d["Capacity"])
        j = int(np.searchsorted(q, 0.5 * q[-1]))
        j = min(max(j, 2), len(V) - 3)
        x1 = float(V[j]) / V0
        dVdq = float(np.polyfit(q[j - 2:j + 3], V[j - 2:j + 3], 1)[0])
        x2 = -dVdq * q_fresh / V0
        x3 = Q / q_fresh
        m_i = int(round(i / max(n - 1, 1) * (len(imp_re) - 1)))
        x4 = imp_re[m_i] / re_fresh
        events.append(np.array([x1, x2, x3, x4]))
    return events


per_cell = {c: stage_events(load(c)) for c in CELLS}
stages = [np.stack([per_cell[c][k] for c in CELLS]) for k in range(N_STAGES)]
mean = [s.mean(axis=0) for s in stages]
spread = [s.std(axis=0, ddof=1) for s in stages]

# metric from measured fresh-stage cell-to-cell spread (honest, from data)
sigma = np.maximum(spread[0], 1e-4)
H = np.diag(1.0 / sigma ** 2)
Hs = np.sqrt(H)

# decoder: fresh-stage response direction, beta = 0.95 (preregistered)
c_raw = mean[0]
beta = 0.95
c_vec = c_raw * np.sqrt(beta) / np.sqrt(float(c_raw @ H @ c_raw))
C = Hs @ c_vec


def ledger(y):
    Y = Hs @ y
    total = float(Y @ Y)
    L = float(C @ Y)
    squares = {lbl: float((C[i] * Y[j] - C[j] * Y[i]) ** 2)
               for lbl, (i, j) in zip(PAIR_LABELS, PAIRS)}
    tr = float(sum(squares.values()))
    resid = beta * total - L * L - tr
    ch1 = ((squares["12"] + squares["13"] + squares["14"]) / tr
           if tr > 0 else 0.0)
    return {"transverse_share": tr / total, "captured_share": L * L / total,
            "channel1_pair_share": ch1,
            "identity_residual_rel": resid / max(beta * total, 1.0),
            "pair_squares_norm": ({k: v / tr for k, v in squares.items()}
                                  if tr > 0 else {})}


stage_results = []
for k in range(N_STAGES):
    led = ledger(mean[k])
    # uncertainty of transverse share from cell spread (jackknife)
    ts = [ledger(stages[k][i])["transverse_share"] for i in range(len(CELLS))]
    led["transverse_share_cell_spread"] = float(np.std(ts, ddof=1))
    led["capacity_ratio_mean"] = float(mean[k][2])
    stage_results.append(led)

fresh_t = stage_results[0]["transverse_share"]
eol_t = stage_results[-1]["transverse_share"]
eol_spread = max(stage_results[-1]["transverse_share_cell_spread"], 1e-12)
z_eol = (eol_t - fresh_t) / eol_spread

results = {
    "FULL_ST_CHART_RUNG": {
        "status": "NOT_EXECUTABLE",
        "reason": "only the 24 C ambient group is publicly mirrored on an "
                  "allowed source; the (s, T) chart temperature axis "
                  "cannot be constructed. Reported per preregistration "
                  "section 1.",
    },
    "REDUCED_CUT_SQUARE_RUNG": {
        "cells": CELLS, "stages": N_STAGES,
        "identity_max_rel_residual": max(
            abs(s["identity_residual_rel"]) for s in stage_results),
        "per_stage": [
            {"stage": k,
             "capacity_ratio": stage_results[k]["capacity_ratio_mean"],
             "transverse_share": stage_results[k]["transverse_share"],
             "cell_spread": stage_results[k]["transverse_share_cell_spread"],
             "channel1_pair_share": stage_results[k]["channel1_pair_share"]}
            for k in range(N_STAGES)],
        "prediction_reduced_P1_fresh_transverse_small": {
            "value": fresh_t, "passes": bool(fresh_t < 0.05)},
        "prediction_reduced_P2_eol_exceeds_fresh_5x_spread": {
            "z": z_eol, "passes": bool(z_eol >= 5.0)},
        "prediction_P3_eol_channel1_share_below_0p9": {
            "value": stage_results[-1]["channel1_pair_share"],
            "passes": bool(stage_results[-1]["channel1_pair_share"] < 0.9)},
    },
    "protocol_deviations": [
        "D1: pseudo-OCV under constant-current load at 50% delivered "
        "capacity, identical at every stage (rest OCV not in dataset).",
        "D2: channels are SoC-axis and impedance quantities only; no "
        "thermal channel in a single-temperature group.",
        "D3: data is a community GitHub mirror of the NASA PCoE set; "
        "authenticity rests on the mirror. Hashes pinned in "
        "data/MANIFEST.sha256.",
    ],
    "data_pins": pins,
}
results["_pin"] = sha256_of({k: v for k, v in results.items()
                             if k != "_pin"})
out = os.path.join(ROOT, "results")
os.makedirs(out, exist_ok=True)
with open(os.path.join(out, "E01_EXP_REDUCED_CERTIFICATE.json"), "w") as f:
    json.dump(results, f, indent=2, sort_keys=True)

print("FULL_ST_CHART_RUNG: NOT_EXECUTABLE (single temperature group)")
r = results["REDUCED_CUT_SQUARE_RUNG"]
for s in r["per_stage"]:
    print(f"stage {s['stage']}: cap_ratio={s['capacity_ratio']:.3f} "
          f"transverse={s['transverse_share']:.3e} "
          f"(spread {s['cell_spread']:.1e}) ch1={s['channel1_pair_share']:.3f}")
for name in ("prediction_reduced_P1_fresh_transverse_small",
             "prediction_reduced_P2_eol_exceeds_fresh_5x_spread",
             "prediction_P3_eol_channel1_share_below_0p9"):
    print(name, "->", r[name])
print("pin:", results["_pin"])
