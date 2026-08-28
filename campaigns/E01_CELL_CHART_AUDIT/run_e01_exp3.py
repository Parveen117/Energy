"""E01-EXP-3: preregistered Kendall-tau + Fisher statistic on CALCE CS2.

Statistic and threshold locked in E01_EXP3_PREREGISTRATION.md, committed
before this data was downloaded. Pipeline: per E01-EXP-R channels with
the Arbin Internal_Resistance column as the resistance channel
(DC-resistance substitution allowed by the preregistration, recorded).
"""

from __future__ import annotations

import glob
import hashlib
import itertools
import json
import os
import re
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(ROOT, "data")
CS2 = "/home/claude/cs2"
sys.path.insert(0, HERE)
from e01_core import sha256_of  # noqa: E402

V0 = 3.7
K = 6
CELLS = ["CS2_33", "CS2_34", "CS2_35", "CS2_36", "CS2_37", "CS2_38"]
PAIRS = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]


def date_key(path):
    # DD-5 (recorded): the first regex captured the cell number as the
    # month and scrambled chronology; the date is the LAST three number
    # groups in the filename (MM_DD_YY).
    nums = re.findall(r"(\d+)", os.path.basename(path))
    mm, dd, yy = (int(x) for x in nums[-3:])
    return (2000 + yy, mm, dd)


def cycle_summaries(cell):
    rows = []
    files = sorted(glob.glob(f"{CS2}/{cell}/*.xls*"), key=date_key)
    for f in files:
        try:
            xl = pd.ExcelFile(f)
        except Exception:
            continue
        for sh in xl.sheet_names:
            if sh.lower().startswith(("info", "statist")):
                continue
            try:
                df = xl.parse(sh, usecols=[
                    "Cycle_Index", "Current(A)", "Voltage(V)",
                    "Discharge_Capacity(Ah)", "Internal_Resistance(Ohm)"])
            except Exception:
                continue
            for ci, g in df.groupby("Cycle_Index"):
                dis = g[g["Current(A)"] < -0.05]
                if len(dis) < 20:
                    continue
                q = dis["Discharge_Capacity(Ah)"].to_numpy()
                Vv = dis["Voltage(V)"].to_numpy()
                order = np.argsort(q)
                q, Vv = q[order], Vv[order]
                # DD-4 (recorded): Discharge_Capacity is cumulative in
                # these Arbin exports; per-cycle capacity is the range
                # within the cycle's discharge rows, not the endpoint.
                q = q - q[0]
                Q = float(q[-1])
                if Q < 0.3:
                    continue
                j = int(np.searchsorted(q, 0.5 * Q))
                j = min(max(j, 3), len(q) - 4)
                sel = slice(max(0, j - 8), min(len(q), j + 9))
                if q[sel].max() - q[sel].min() < 1e-4:
                    continue
                co = np.polyfit(q[sel], Vv[sel], 1)
                r_col = g["Internal_Resistance(Ohm)"]
                r_col = r_col[r_col > 0]
                R = float(r_col.median()) if len(r_col) else np.nan
                rows.append({"V50": float(np.polyval(co, 0.5 * Q)),
                             "slope": float(co[0]), "Q": Q, "R": R})
    return rows


def stage_events(cell):
    rows = cycle_summaries(cell)
    rows = [r for r in rows if np.isfinite(r["R"])]
    n = len(rows)
    assert n >= 3 * K, f"{cell}: only {n} usable cycles"
    q_fresh = rows[0]["Q"]
    r_fresh = rows[0]["R"]
    evs = []
    for k in range(K):
        i = int(round(k * (n - 1) / (K - 1)))
        r = rows[i]
        evs.append(np.array([r["V50"] / V0,
                             -r["slope"] * q_fresh / V0,
                             r["Q"] / q_fresh,
                             r["R"] / r_fresh]))
    return evs


per_cell = {c: stage_events(c) for c in CELLS}
fresh = np.stack([per_cell[c][0] for c in CELLS])
sigma = np.maximum(fresh.std(axis=0, ddof=1), 1e-4)
H = np.diag(1.0 / sigma ** 2)
Hs = np.sqrt(H)
c_raw = fresh.mean(axis=0)
beta = 0.95
c_vec = c_raw * np.sqrt(beta) / np.sqrt(float(c_raw @ H @ c_raw))
C = Hs @ c_vec


def transverse_share(y):
    Y = Hs @ y
    tot = float(Y @ Y)
    tr = sum((C[i] * Y[j] - C[j] * Y[i]) ** 2 for i, j in PAIRS)
    return float(tr) / tot


def kendall_tau(vals):
    n = len(vals)
    conc = disc = 0
    for a, b in itertools.combinations(range(n), 2):
        d = vals[b] - vals[a]
        conc += d > 0
        disc += d < 0
    return (conc - disc) / (n * (n - 1) / 2)


PERMS = list(itertools.permutations(range(K)))
TAUS = sorted(kendall_tau(list(p)) for p in PERMS)


def exact_p(tau):
    return sum(1 for t in TAUS if t >= tau - 1e-12) / len(TAUS)


per = {}
X = 0.0
for c in CELLS:
    T = [transverse_share(per_cell[c][k]) for k in range(K)]
    tau = kendall_tau(T)
    p = exact_p(tau)
    X += -2.0 * np.log(p)
    per[c] = {"transverse_by_stage": T, "kendall_tau": tau,
              "exact_p": p,
              "capacity_ratio_eol": float(per_cell[c][K - 1][2])}

from scipy.stats import chi2  # noqa: E402
p_combined = float(chi2.sf(X, 2 * len(CELLS)))
PASS = p_combined < 1e-6

results = {
    "statistic": "per-cell Kendall tau of transverse share vs stage; "
                 "exact permutation p (720 arrangements); Fisher "
                 "combination, chi-square 12 dof",
    "per_cell": per,
    "fisher_X": X,
    "combined_p": p_combined,
    "threshold": 1e-6,
    "PREDICTION_EXP3_P": {
        "passes": bool(PASS),
        "status": "CERTIFIED_AGING_TREND" if PASS else "FAILED",
    },
    "deviations": [
        "DC internal-resistance column substituted for EIS (allowed by "
        "preregistration).",
        "D1 pseudo-OCV under load carried over.",
        "DD-4: cumulative Discharge_Capacity column; per-cycle capacity taken as within-cycle range (first run produced impossible capacity ratios ~54 and was discarded as a parsing defect before any verdict was accepted).",
        "DD-5: filename date regex captured the cell number as month, scrambling chronology; fixed to the last three number groups. Both defect runs discarded before accepting a verdict.",
    ],
}
results["_pin"] = sha256_of({k: v for k, v in results.items()
                             if k != "_pin"})
with open(os.path.join(ROOT, "results", "E01_EXP3_CERTIFICATE.json"),
          "w") as f:
    json.dump(results, f, indent=2, sort_keys=True)

for c in CELLS:
    r = per[c]
    print(f"{c}: tau={r['kendall_tau']:+.2f} p={r['exact_p']:.4f} "
          f"cap_eol={r['capacity_ratio_eol']:.2f} "
          f"T=[{', '.join(f'{t:.2e}' for t in r['transverse_by_stage'])}]")
print(f"Fisher X={X:.1f}  combined p={p_combined:.2e}  "
      f"-> {results['PREDICTION_EXP3_P']['status']}")
print("pin:", results["_pin"])
