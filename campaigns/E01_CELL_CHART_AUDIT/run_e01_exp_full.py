"""E01-EXP-F: FULL (s, T) Pluecker rung on real NASA PCoE data.

Executes the original E01_EXP_PREREGISTRATION full rung now that three
ambient-temperature groups are pinned: 24 C (B0005/6/7), 43 C
(B0029-32), 4 C (B0045-48).

Recorded deviations (beyond D1-D3 of EXP-R):
- D4 (channel set, mathematical reason): the capacity-ratio channel
  has zero SoC-gradient at fixed stage, and the EIS resistance channel
  has no measured SoC-gradient; two zero rows in the s-gradient make
  the Pfaffian vanish identically and the audit vacuous. The full-rung
  channels are therefore curve-based: V(0.5)/V0, first and second
  nondimensional derivatives of the discharge curve at 50% DoD, and
  Re/Re_ref. Exactly one s-blind channel (Re) is retained, which does
  not degenerate the identity.
- D5 (stage matching): slots are matched by stage FRACTION of each
  group's own filtered discharge count, not by matched SOH; the 43 C
  group was stopped before end of life.
- D6 (T stencil): the temperature derivative is a two-point difference
  between the 4 C and 43 C groups (different physical cells); the
  within-group cell-to-cell spread at each stage is the declared noise
  term, per preregistration section 2.

Statistics unchanged: raw Pluecker residual, 300-draw SE, 5 sigma,
2,000-draw bootstrap on any rejection.
"""

from __future__ import annotations

import glob
import hashlib
import json
import os
import sys

import numpy as np
from scipy.io import loadmat

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(ROOT, "data")
NASA = "/home/claude/nasa_x"
sys.path.insert(0, HERE)
from e01_core import PAIRS, REJECTION_SIGMA, sha256_of, verdict  # noqa

V0 = 3.7
N_STAGES = 6
GROUPS = {
    277.15: ["B0045", "B0046", "B0047", "B0048"],   # 4 C
    297.15: ["B0005", "B0006", "B0007"],            # 24 C
    316.15: ["B0029", "B0030", "B0031", "B0032"],   # 43 C
}
T_LO, T_MID, T_HI = 277.15, 297.15, 316.15
AMBIENT = {277.15: 4, 297.15: 24, 316.15: 43}


def find_mat(name):
    hits = glob.glob(f"{NASA}/**/{name}.mat", recursive=True)
    return hits[0]


def cell_stage_channels(name, ambient, re_ref):
    """Per stage k: (x1, x2, x3, x4) from this cell's own life."""
    m = loadmat(find_mat(name), simplify_cells=True)
    cyc = m[name]["cycle"]
    dis = [c for c in cyc if c["type"] == "discharge"
           and c.get("ambient_temperature") == ambient
           and "Capacity" in c.get("data", {})]
    imp = [c for c in cyc if c["type"] == "impedance"
           and "Re" in c.get("data", {})]
    imp_re = [float(np.real(np.atleast_1d(c["data"]["Re"])).min())
              for c in imp]
    n = len(dis)
    out = []
    for k in range(N_STAGES):
        i = int(round(k * (n - 1) / (N_STAGES - 1)))
        d = dis[i]["data"]
        V = np.asarray(d["Voltage_measured"], float)
        t = np.asarray(d["Time"], float)
        I = np.asarray(d["Current_measured"], float)
        q = np.concatenate([[0.0],
                            np.cumsum(np.abs(I[:-1]) * np.diff(t)) / 3600.0])
        qq = q / q[-1]
        # smooth local polynomial around 50% DoD for V, V', V''
        sel = (qq > 0.35) & (qq < 0.65)
        if sel.sum() < 8:
            sel = (qq > 0.25) & (qq < 0.75)
        co = np.polyfit(qq[sel] - 0.5, V[sel], 3)
        # cubic: V = c0 x^3 + c1 x^2 + c2 x + c3 around x = qq - 0.5
        x1 = float(co[3]) / V0
        x2 = -float(co[2]) / V0
        x3 = float(2.0 * co[1]) / V0
        x3p = float(6.0 * co[0]) / V0     # dV''/ds = 6 c0 (third deriv)
        m_i = int(round(i / max(n - 1, 1) * (len(imp_re) - 1)))
        x4 = imp_re[m_i] / re_ref
        out.append((np.array([x1, x2, x3, x4]), x3p))
    return out


# reference resistance: fresh 24 C group mean
def fresh_re(names, ambient):
    vals = []
    for nm in names:
        m = loadmat(find_mat(nm), simplify_cells=True)
        cyc = m[nm]["cycle"]
        imp = [c for c in cyc if c["type"] == "impedance"
               and "Re" in c.get("data", {})]
        vals.append(float(np.real(np.atleast_1d(imp[0]["data"]["Re"])).min()))
    return float(np.mean(vals))


RE_REF = fresh_re(GROUPS[T_MID], 24)

# group -> per stage: mean channels and cell spread
group_stage = {}
for T, names in GROUPS.items():
    per = [cell_stage_channels(nm, AMBIENT[T], RE_REF) for nm in names]
    group_stage[T] = {
        "mean": [np.mean([p[k][0] for p in per], axis=0)
                 for k in range(N_STAGES)],
        "spread": [np.std([p[k][0] for p in per], axis=0, ddof=1)
                   for k in range(N_STAGES)],
        "x3p": [float(np.mean([p[k][1] for p in per]))
                for k in range(N_STAGES)],
        "x3p_spread": [float(np.std([p[k][1] for p in per], ddof=1))
                       for k in range(N_STAGES)],
    }

DS = 0.05  # SoC half-step for the s-gradient (via the fitted polynomial)


def slot_gradients(k, rng=None):
    """Chart gradients for slot k, optionally noise-perturbed."""
    def val(T, dk=0.0):
        x = group_stage[T]["mean"][k].copy()
        if rng is not None:
            x = x + rng.normal(0.0, group_stage[T]["spread"][k])
        return x
    # s-gradient at mid temperature: differentiate the polynomial
    # channels analytically via a second fit is equivalent to using
    # (x1', x2', x3') relations; here reuse x2, x3 as derivatives:
    xm = val(T_MID)
    x3p = group_stage[T_MID]["x3p"][k]
    if rng is not None:
        x3p = x3p + rng.normal(0.0, group_stage[T_MID]["x3p_spread"][k])
    u = np.array([-xm[1], -xm[2], x3p, 0.0])
    # Implementation defect DD-3 (recorded): the first implementation
    # fit a quadratic, left u[2]=0 alongside the s-blind Re row, and
    # the Pfaffian was identically zero. Fixed by the cubic fit whose
    # leading coefficient supplies dV''/ds; Re remains the single
    # s-blind channel, which does not degenerate the identity.
    # temperature gradient: two-point across groups
    v = (val(T_HI) - val(T_LO)) / (T_HI - T_LO)
    return u, v


def brackets_for_slots(rng=None):
    B = {}
    for (i, j), k in zip(PAIRS, range(6)):
        u, v = slot_gradients(k, rng)
        B[f"B{i+1}{j+1}"] = u[i] * v[j] - u[j] * v[i]
    return B


def residual(B):
    return B["B12"] * B["B34"] - B["B13"] * B["B24"] + B["B14"] * B["B23"]


# rank sanity: u has two zero entries (x3-slope declared 0, x4 s-blind)
u0, v0 = slot_gradients(0)
rank_ok = np.linalg.matrix_rank(np.stack([u0, v0]), tol=1e-12) == 2
degenerate = (abs(u0[2]) < 1e-15 and abs(u0[3]) < 1e-15)

results = {"_deviations": ["D4 curve-based channels (degeneracy reason)",
                           "D5 stage-fraction matching",
                           "D6 cross-group T stencil; cell spread as noise"]}

if degenerate:
    # two zero rows in u -> Pfaffian identically zero: record honestly
    # and use the three-channel + Re reduced identity instead? No: the
    # preregistered statistic is the 4-channel Pfaffian; if the s-grad
    # has two zero entries the full rung is VACUOUS and must be said so.
    results["FULL_ST_RUNG"] = {
        "status": "VACUOUS_DEGENERATE",
        "reason": "s-gradient has two structurally zero entries (V'' "
                  "third-derivative not estimated; Re has no SoC "
                  "dependence in EIS-at-rest data); the Pfaffian then "
                  "vanishes identically and the audit has no power. "
                  "Recorded rather than silently re-parameterized.",
    }
else:
    rng = np.random.default_rng(7)
    B = brackets_for_slots()
    r = residual(B)
    draws = [residual(brackets_for_slots(np.random.default_rng(1000 + i)))
             for i in range(300)]
    se = float(np.std(draws, ddof=1))
    z = r / se if se > 0 else float("inf")
    entry = {"raw_residual": r, "noise_standard_error": se, "z_score": z,
             "rejection_threshold": REJECTION_SIGMA, "status": verdict(z)}
    if entry["status"] == "FALSIFIED_MEASUREMENT_CONTRACT":
        boot = [residual(brackets_for_slots(np.random.default_rng(5000 + i)))
                for i in range(2000)]
        lo, hi = np.percentile(boot, [0.05, 99.95])
        entry["bootstrap"] = {"n_draws": 2000,
                              "p999_interval": [float(lo), float(hi)],
                              "zero_inside_99p9": bool(lo <= 0.0 <= hi)}
    results["FULL_ST_RUNG_AGING_SLOTS"] = entry

    # control: all six slots at the fresh stage (k=0), disjoint pairs
    def brackets_fresh(rng=None):
        B = {}
        for (i, j) in PAIRS:
            u, v = slot_gradients(0, rng)
            B[f"B{i+1}{j+1}"] = u[i] * v[j] - u[j] * v[i]
        return B
    r0 = residual(brackets_fresh())
    d0 = [residual(brackets_fresh(np.random.default_rng(9000 + i)))
          for i in range(300)]
    se0 = float(np.std(d0, ddof=1))
    results["FULL_ST_RUNG_FRESH_CONTROL"] = {
        "raw_residual": r0, "noise_standard_error": se0,
        "z_score": r0 / se0 if se0 > 0 else 0.0,
        "status": verdict(r0 / se0 if se0 > 0 else 0.0),
    }

results["_meta"] = {
    "groups_K": {str(t): g for t, g in
                 ((t, GROUPS[t]) for t in GROUPS)},
    "re_ref_ohm_fresh24C": RE_REF,
    "chart_point": {"s": 0.5, "T_K": T_MID},
    "framework_sources": ["arXiv:2603.20773 rank-2 area-bracket theorem"],
}
results["_pin"] = sha256_of({k: v for k, v in results.items()
                             if k != "_pin"})
with open(os.path.join(ROOT, "results",
                       "E01_EXP_FULL_ST_CERTIFICATE.json"), "w") as f:
    json.dump(results, f, indent=2, sort_keys=True)
for k, v in results.items():
    if k.startswith("_"):
        continue
    print(k, "->", v.get("status"), "" if "z_score" not in v
          else f"z={v['z_score']:+.1f}")
print("pin:", results["_pin"])
