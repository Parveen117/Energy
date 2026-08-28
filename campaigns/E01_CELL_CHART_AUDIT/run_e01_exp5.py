"""E01-EXP-5: whitened (s, T) chart audit (AF-2 remedy, preregistered)."""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
from e01_core import PAIRS, REJECTION_SIGMA, sha256_of, verdict  # noqa
import run_e01_exp4 as X4  # reuse loaded A123/INR branches and channel fns

S0 = X4.S0

# declared whitening scales: replicate (cell 007 vs 008 at 25 C) spread
# of chart-point channel values, over three decimated windows
vals7 = [X4.a123_channels(25, "A1-007", S0, k) for k in range(3)]
vals8 = [X4.a123_channels(25, "A1-008", S0, k) for k in range(3)]
SCALE = np.maximum(np.abs(np.array(vals7) - np.array(vals8)).mean(axis=0)
                   / np.sqrt(2.0), 1e-6)


def wA(Tc, cell, s0, k):
    return X4.a123_channels(Tc, cell, s0, k) / SCALE


def wI(Tc, s0, k):
    return X4.inr_channels(Tc, s0, k) / SCALE


DS = 0.05


def grad_a123(k):
    cells = sorted(X4.a123[25])
    cell = cells[k % 2]
    u = (wA(25, cell, S0 + DS, k) - wA(25, cell, S0 - DS, k)) / (2 * DS)
    cl = sorted(X4.a123[10])[k % 2]
    ch = sorted(X4.a123[30])[k % 2]
    v = (wA(30, ch, S0, k) - wA(10, cl, S0, k)) / 20.0
    return u, v


def grad_mix(k):
    if k % 2 == 0:
        return grad_a123(k)
    u = (wI(25, S0 + DS, k) - wI(25, S0 - DS, k)) / (2 * DS)
    v = (wI(45, S0, k) - wI(0, S0, k)) / 45.0
    return u, v


# replicate gradient noise in whitened units (preregistered AF-1 remedy)
def replicate_grad_noise():
    du, dv = [], []
    for k in range(3):
        uA = (wA(25, "A1-007", S0 + DS, k) - wA(25, "A1-007", S0 - DS, k)) / (2 * DS)
        uB = (wA(25, "A1-008", S0 + DS, k) - wA(25, "A1-008", S0 - DS, k)) / (2 * DS)
        vA = (wA(30, "A1-007", S0, k) - wA(10, "A1-007", S0, k)) / 20.0
        vB = (wA(30, "A1-008", S0, k) - wA(10, "A1-008", S0, k)) / 20.0
        du.append(np.abs(uA - uB) / np.sqrt(2))
        dv.append(np.abs(vA - vB) / np.sqrt(2))
    return (np.maximum(np.mean(du, axis=0), 1e-9),
            np.maximum(np.mean(dv, axis=0), 1e-9))


NU, NV = replicate_grad_noise()


def brackets(gradfn, rng=None):
    B = {}
    for (i, j), k in zip(PAIRS, range(6)):
        u, v = gradfn(k)
        if rng is not None:
            u = u + rng.normal(0.0, NU)
            v = v + rng.normal(0.0, NV)
        B[f"B{i+1}{j+1}"] = u[i] * v[j] - u[j] * v[i]
    return B


def residual(B):
    return B["B12"] * B["B34"] - B["B13"] * B["B24"] + B["B14"] * B["B23"]


def norm_res(B):
    b = np.array([B[k] for k in ("B12", "B13", "B14", "B23", "B24", "B34")])
    return abs(residual(B)) / max(float(b @ b), 1e-30)


results = {"_whitening_scales": SCALE.tolist()}
for name, fn, in (("EXP5A_A123_WHITENED", grad_a123),
                  ("EXP5B_CHEMISTRY_MIX_WHITENED", grad_mix)):
    B = brackets(fn)
    r = residual(B)
    draws = [residual(brackets(fn, np.random.default_rng(1000 + i)))
             for i in range(300)]
    se = float(np.std(draws, ddof=1))
    z = r / se if se > 0 else float("inf")
    entry = {"raw_residual": r, "normalized_residual_T01": norm_res(B),
             "noise_standard_error": se, "z_score": z,
             "rejection_threshold": REJECTION_SIGMA, "status": verdict(z)}
    if entry["status"] == "FALSIFIED_MEASUREMENT_CONTRACT":
        boot = [residual(brackets(fn, np.random.default_rng(5000 + i)))
                for i in range(2000)]
        lo, hi = np.percentile(boot, [0.05, 99.95])
        entry["bootstrap"] = {"n_draws": 2000,
                              "p999_interval": [float(lo), float(hi)],
                              "zero_inside_99p9": bool(lo <= 0.0 <= hi)}
    results[name] = entry
    print(name, "->", entry["status"], f"z={z:+.1f}",
          f"norm={entry['normalized_residual_T01']:.3e}")

results["_meta"] = {"preregistration": "E01_EXP5_PREREGISTRATION.md",
                    "audit_basis": "AUDIT_CROSS_REPO.md AF-1/AF-2"}
results["_pin"] = sha256_of({k: v for k, v in results.items()
                             if k != "_pin"})
with open(os.path.join(ROOT, "results", "E01_EXP5_CERTIFICATE.json"),
          "w") as f:
    json.dump(results, f, indent=2, sort_keys=True)
print("pin:", results["_pin"])
