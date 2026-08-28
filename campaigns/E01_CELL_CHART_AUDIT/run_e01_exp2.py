"""E01-EXP-2: exact per-cell monotonicity statistic (preregistered).

Statistic and threshold fixed in E01_EXP2_PREREGISTRATION.md, committed
before this file computes anything. Pipeline identical to E01-EXP-R.
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
from e01_core import sha256_of

V0 = 3.7
N_STAGES = 6
CELLS = ["B0005", "B0006", "B0007", "B0018"]
PAIRS = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]

pins = {}
for line in open(os.path.join(DATA, "MANIFEST.sha256")):
    if line.strip():
        h, rel = line.strip().split(maxsplit=1)
        p = os.path.join(DATA, rel)
        assert hashlib.sha256(open(p, "rb").read()).hexdigest() == h, rel
        pins[rel] = h


def load(name):
    m = loadmat(os.path.join(DATA, "raw", f"{name}.mat"), simplify_cells=True)
    return m[name]["cycle"]


def stage_events(cycles):
    dis = [c for c in cycles if c["type"] == "discharge"
           and "Capacity" in c.get("data", {})]
    imp = [c for c in cycles if c["type"] == "impedance"
           and "Re" in c.get("data", {})]
    imp_re = [float(np.real(np.atleast_1d(c["data"]["Re"])).min())
              for c in imp]
    n = len(dis)
    idxs = [int(round(k * (n - 1) / (N_STAGES - 1))) for k in range(N_STAGES)]
    q_fresh = float(dis[0]["data"]["Capacity"])
    re_fresh = imp_re[0]
    events = []
    for i in idxs:
        d = dis[i]["data"]
        V = np.asarray(d["Voltage_measured"], float)
        t = np.asarray(d["Time"], float)
        I = np.asarray(d["Current_measured"], float)
        q = np.concatenate([[0.0],
                            np.cumsum(np.abs(I[:-1]) * np.diff(t)) / 3600.0])
        j = int(np.searchsorted(q, 0.5 * q[-1]))
        j = min(max(j, 2), len(V) - 3)
        x1 = float(V[j]) / V0
        dVdq = float(np.polyfit(q[j - 2:j + 3], V[j - 2:j + 3], 1)[0])
        x2 = -dVdq * q_fresh / V0
        x3 = float(d["Capacity"]) / q_fresh
        m_i = int(round(i / max(n - 1, 1) * (len(imp_re) - 1)))
        x4 = imp_re[m_i] / re_fresh
        events.append(np.array([x1, x2, x3, x4]))
    return events


per_cell = {c: stage_events(load(c)) for c in CELLS}
stages = [np.stack([per_cell[c][k] for c in CELLS]) for k in range(N_STAGES)]
sigma = np.maximum(stages[0].std(axis=0, ddof=1), 1e-4)
H = np.diag(1.0 / sigma ** 2)
Hs = np.sqrt(H)
c_raw = stages[0].mean(axis=0)
beta = 0.95
c_vec = c_raw * np.sqrt(beta) / np.sqrt(float(c_raw @ H @ c_raw))
C = Hs @ c_vec


def transverse_share(y):
    Y = Hs @ y
    total = float(Y @ Y)
    tr = sum((C[i] * Y[j] - C[j] * Y[i]) ** 2 for i, j in PAIRS)
    return float(tr) / total


T = {c: [transverse_share(per_cell[c][k]) for k in range(N_STAGES)]
     for c in CELLS}

per_cell_result = {}
all_monotonic = True
for c in CELLS:
    vals = T[c]
    breaks = [(k, vals[k], vals[k + 1]) for k in range(N_STAGES - 1)
              if not vals[k + 1] > vals[k]]
    per_cell_result[c] = {
        "transverse_by_stage": vals,
        "strictly_increasing": not breaks,
        "breaks": [{"transition": f"{k}->{k+1}", "from": a, "to": b}
                   for k, a, b in breaks],
        "growth_factor_stage1_to_eol": vals[5] / max(vals[1], 1e-12),
    }
    if breaks:
        all_monotonic = False

results = {
    "statistic": "per-cell strict monotonicity of cut-square transverse "
                 "share across six life stages (Kendall tau = 1)",
    "null": "stage exchangeability; P(strictly increasing) = 1/720 per "
            "cell; joint (1/720)^4 = 3.72e-12",
    "per_cell": per_cell_result,
    "PREDICTION_EXP2_P": {
        "all_four_cells_strictly_increasing": all_monotonic,
        "exact_null_probability_if_pass": (1.0 / 720.0) ** 4,
        "status": "CERTIFIED_AGING_TREND" if all_monotonic
        else "FAILED_SEE_BREAKS",
    },
    "pipeline": "identical to E01-EXP-R; deviations D1-D3 carried over",
    "data_pins": pins,
}
results["_pin"] = sha256_of({k: v for k, v in results.items()
                             if k != "_pin"})
out = os.path.join(ROOT, "results")
with open(os.path.join(out, "E01_EXP2_CERTIFICATE.json"), "w") as f:
    json.dump(results, f, indent=2, sort_keys=True)

for c in CELLS:
    r = per_cell_result[c]
    marks = " ".join(f"{v:.2e}" for v in r["transverse_by_stage"])
    print(f"{c}: {'MONOTONIC' if r['strictly_increasing'] else 'BREAK'} "
          f"[{marks}] growth x{r['growth_factor_stage1_to_eol']:.0f}")
    for b in r["breaks"]:
        print("   break:", b)
print("EXP2-P:", results["PREDICTION_EXP2_P"]["status"])
print("pin:", results["_pin"])
