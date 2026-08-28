"""E01-EXP-4: fresh (s, T) chart audit on true rest-OCV data.

Preregistered in E01_EXP4_PREREGISTRATION.md (committed before these
files were opened). EXP4-A: A123 single-chemistry chart, prediction
NOT_FALSIFIED. EXP4-B: A123/INR chemistry mix on one claimed chart,
prediction FALSIFIED. Statistics identical to E01.
"""

from __future__ import annotations

import glob
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(ROOT, "data")
A123 = os.path.join(DATA, "extracted", "a123")
INR = os.path.join(DATA, "extracted", "inr")
sys.path.insert(0, HERE)
from e01_core import PAIRS, REJECTION_SIGMA, sha256_of, verdict  # noqa

V0 = 3.7
S0 = 0.5


def read_arbin(path):
    try:
        xl = pd.ExcelFile(path)
    except Exception:
        conv = os.path.splitext(path)[0] + ".xlsx"
        if not os.path.exists(conv):
            subprocess.run(["python", "/mnt/skills/public/xlsx/scripts/office/soffice.py"
                            ] if False else
                           ["soffice", "--headless", "--convert-to", "xlsx",
                            "--outdir", os.path.dirname(path), path],
                           capture_output=True, timeout=300)
            conv = os.path.splitext(path)[0] + ".xlsx"
        xl = pd.ExcelFile(conv)
    sh = [s for s in xl.sheet_names
          if not s.lower().startswith(("info", "statist", "sheet"))]
    frames = [xl.parse(s, usecols=lambda c: c in (
        "Step_Index", "Current(A)", "Voltage(V)",
        "Charge_Capacity(Ah)", "Discharge_Capacity(Ah)"))
        for s in (sh or xl.sheet_names[:1])]
    return pd.concat(frames, ignore_index=True)


def branches(df):
    """Return (s, V) for the slow discharge and charge branches."""
    out = {}
    for label, sign in (("dis", -1), ("chg", +1)):
        g = df[(df["Current(A)"] * sign > 0.01)
               & (df["Current(A)"].abs() < 0.5)]
        if len(g) < 200:
            continue
        col = ("Discharge_Capacity(Ah)" if sign < 0
               else "Charge_Capacity(Ah)")
        q = g[col].to_numpy(float)
        q = q - q.min()
        V = g["Voltage(V)"].to_numpy(float)
        if q.max() <= 0:
            continue
        s = 1.0 - q / q.max() if sign < 0 else q / q.max()
        order = np.argsort(s)
        out[label] = (s[order], V[order])
    return out


def channels_at(br, s0, sel_mask=None):
    """x1..x4 at SoC s0 from the two branches via cubic local fits."""
    def fit(s, V):
        sel = (s > s0 - 0.15) & (s < s0 + 0.15)
        if sel_mask is not None:
            idx = np.where(sel)[0]
            sel2 = np.zeros_like(sel)
            sel2[idx[sel_mask % 3::3]] = True
            sel = sel2
        co = np.polyfit(s[sel] - s0, V[sel], 3)
        return (float(co[3]), float(co[2]), float(2 * co[1]))
    vd = fit(*br["dis"])
    vc = fit(*br["chg"])
    ocv = tuple((a + b) / 2 for a, b in zip(vd, vc))
    hys = (vc[0] - vd[0]) / 2
    return np.array([ocv[0] / V0, ocv[1] / V0, ocv[2] / V0, hys / V0])


# ---------------- load A123: 8 temperatures x 2 cells ----------------
a123 = {}
for d in sorted(glob.glob(f"{A123}/OCV*")):
    base = os.path.basename(d)
    Tc = int(base.split("-")[0].replace("OCV", "") or "-10") \
        if not base.startswith("OCV-10") else -10
    cells = {}
    for f in glob.glob(f"{d}/A1-0*.xlsx"):
        if os.path.basename(f).startswith("~$"):
            continue
        br = branches(read_arbin(f))
        if "dis" in br and "chg" in br:
            cells[os.path.basename(f)[:6]] = br
    if cells:
        a123[Tc] = cells
TEMPS = sorted(a123)
print("A123 temperatures:", TEMPS, "cells per T:",
      {t: sorted(a123[t]) for t in TEMPS}, file=sys.stderr)

T0C = 25
TLO, THI = 10, 30


def a123_channels(Tc, cell, s0, sel=None):
    return channels_at(a123[Tc][cell], s0, sel)


def slot_gradients_a123(k, rng=None):
    cells = sorted(a123[T0C])
    cell = cells[k % len(cells)]
    ds = 0.05
    u = (a123_channels(T0C, cell, S0 + ds, k)
         - a123_channels(T0C, cell, S0 - ds, k)) / (2 * ds)
    cl = sorted(a123[TLO])[k % len(a123[TLO])]
    ch = sorted(a123[THI])[k % len(a123[THI])]
    v = (a123_channels(THI, ch, S0, k)
         - a123_channels(TLO, cl, S0, k)) / (THI - TLO)
    if rng is not None:
        u = u + rng.normal(0.0, NOISE_U)
        v = v + rng.normal(0.0, NOISE_V)
    return u, v


def residual(B):
    return B["B12"] * B["B34"] - B["B13"] * B["B24"] + B["B14"] * B["B23"]


def brackets(gradfn, rng=None):
    B = {}
    for (i, j), k in zip(PAIRS, range(6)):
        u, v = gradfn(k, rng)
        B[f"B{i+1}{j+1}"] = u[i] * v[j] - u[j] * v[i]
    return B


# noise term: spread between the two cells' gradient estimates
def measure_noise(gradfn):
    us, vs = [], []
    for k in range(6):
        u, v = gradfn(k)
        us.append(u)
        vs.append(v)
    return (np.std(us, axis=0, ddof=1), np.std(vs, axis=0, ddof=1))


NOISE_U, NOISE_V = measure_noise(slot_gradients_a123)
NOISE_U = np.maximum(NOISE_U, 1e-6)
NOISE_V = np.maximum(NOISE_V, 1e-8)

results = {}


def run_rung(name, gradfn):
    r = residual(brackets(gradfn))
    draws = [residual(brackets(gradfn, np.random.default_rng(1000 + i)))
             for i in range(300)]
    se = float(np.std(draws, ddof=1))
    z = r / se if se > 0 else float("inf")
    entry = {"raw_residual": r, "noise_standard_error": se,
             "z_score": z, "rejection_threshold": REJECTION_SIGMA,
             "status": verdict(z)}
    if entry["status"] == "FALSIFIED_MEASUREMENT_CONTRACT":
        boot = [residual(brackets(gradfn, np.random.default_rng(5000 + i)))
                for i in range(2000)]
        lo, hi = np.percentile(boot, [0.05, 99.95])
        entry["bootstrap"] = {"n_draws": 2000,
                              "p999_interval": [float(lo), float(hi)],
                              "zero_inside_99p9": bool(lo <= 0.0 <= hi)}
    results[name] = entry
    print(name, "->", entry["status"], f"z={z:+.1f}")


run_rung("EXP4A_A123_SINGLE_CHART", slot_gradients_a123)

# ---------------- INR: rest-OCV extraction from incremental protocol ----
def inr_rest_branches(df):
    """True rest OCV: last sample of each rest period in the discharge
    (step 6) and charge (step 10) rest steps, vs normalized capacity."""
    out = {}
    for label, step, col, sgn in (("dis", 6, "Discharge_Capacity(Ah)", -1),
                                  ("chg", 10, "Charge_Capacity(Ah)", +1)):
        g = df[df["Step_Index"] == step]
        if len(g) < 100:
            continue
        q = g[col].to_numpy(float)
        V = g["Voltage(V)"].to_numpy(float)
        # split rests where capacity value jumps
        cuts = np.where(np.abs(np.diff(q)) > 1e-4)[0]
        ends = list(cuts) + [len(q) - 1]
        qs = np.array([q[e] for e in ends])
        Vs = np.array([V[e] for e in ends])
        qs = qs - qs.min()
        if qs.max() <= 0 or len(qs) < 8:
            continue
        s = 1.0 - qs / qs.max() if sgn < 0 else qs / qs.max()
        o = np.argsort(s)
        out[label] = (s[o], Vs[o])
    return out


# temperature encoded in the file DATE (per CALCE listing):
# 12_2_2015 -> 25 C, 12_09_2015 -> 45 C, 02/03_2016 -> 0 C
def inr_temp(fname):
    b = os.path.basename(fname)
    if b.startswith("12_2_"):
        return 25
    if b.startswith("12_09_"):
        return 45
    return 0


inr = {}
for f in glob.glob(f"{INR}/*ncrement*"):
    low = os.path.basename(f).lower()
    Tc = inr_temp(f)
    sp = "SP1" if "sp20-1" in low else "SP3"
    try:
        br = inr_rest_branches(read_arbin(f))
    except Exception as e:
        print("INR read fail", os.path.basename(f), str(e)[:60],
              file=sys.stderr)
        continue
    if "dis" in br and "chg" in br:
        inr.setdefault(Tc, {})[sp] = br
print("INR temps:", {t: sorted(v) for t, v in inr.items()}, file=sys.stderr)

if 25 in inr and 0 in inr and 45 in inr:
    def inr_channels(Tc, s0, sel=None):
        sp = sorted(inr[Tc])[0]
        br = inr[Tc][sp]
        def fit(sv, Vv):
            sel2 = (sv > s0 - 0.3) & (sv < s0 + 0.3)
            co = np.polyfit(sv[sel2] - s0, Vv[sel2],
                            3 if sel2.sum() >= 6 else 2)
            if len(co) == 3:
                co = np.concatenate([[0.0], co])
            return (float(co[3]), float(co[2]), float(2 * co[1]))
        vd = fit(*br["dis"])
        vc = fit(*br["chg"])
        ocv = tuple((a + b) / 2 for a, b in zip(vd, vc))
        return np.array([ocv[0] / V0, ocv[1] / V0, ocv[2] / V0,
                         (vc[0] - vd[0]) / 2 / V0])

    def slot_gradients_mix(k, rng=None):
        ds = 0.05
        if k % 2 == 0:
            u, v = slot_gradients_a123(k)
        else:
            u = (inr_channels(25, S0 + ds, k)
                 - inr_channels(25, S0 - ds, k)) / (2 * ds)
            v = (inr_channels(45, S0, k)
                 - inr_channels(0, S0, k)) / 45.0
        if rng is not None:
            u = u + rng.normal(0.0, NOISE_U)
            v = v + rng.normal(0.0, NOISE_V)
        return u, v

    run_rung("EXP4B_CHEMISTRY_MIX", slot_gradients_mix)
else:
    results["EXP4B_CHEMISTRY_MIX"] = {
        "status": "NOT_EXECUTABLE",
        "reason": f"INR branches unavailable at all three temperatures "
                  f"(found {sorted(inr)}); recorded as is.",
    }
    print("EXP4B -> NOT_EXECUTABLE", sorted(inr))

results["_meta"] = {
    "chart_point": {"s": S0, "T_C": T0C},
    "a123_temperatures_C": TEMPS,
    "noise_term": "cross-slot spread of gradient estimates (two cells, "
                  "decimated windows)",
    "framework_sources": ["arXiv:2603.20773 rank-2 area-bracket theorem"],
    "preregistration": "E01_EXP4_PREREGISTRATION.md",
}
results["_pin"] = sha256_of({k: v for k, v in results.items()
                             if k != "_pin"})
with open(os.path.join(ROOT, "results", "E01_EXP4_CERTIFICATE.json"),
          "w") as f:
    json.dump(results, f, indent=2, sort_keys=True)
print("pin:", results["_pin"])
