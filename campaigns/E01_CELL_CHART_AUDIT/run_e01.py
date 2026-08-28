"""Run rungs E01A-E01E and write the pinned certificate."""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from e01_core import (PAIRS, REJECTION_SIGMA, CellModel, brackets_common,
                      channels, cut_square_ledger, declared_decoder,
                      gradients, independent_brackets, noise_standard_error,
                      pluecker_residual, response_event, sha256_of, verdict)

S0, T0, DS, DT = 0.5, 298.15, 0.05, 5.0
fresh = CellModel()
results = {}


def clean(s, T):
    return channels(fresh, s, T)


# ---- E01A: common-gradient algebraic control ----
u, v = gradients(clean, S0, T0, DS, DT)
rA = pluecker_residual(brackets_common(u, v))
results["E01A_COMMON_GRADIENT_CONTROL"] = {
    "raw_residual": rA,
    "status": "PASS_CONTROL" if abs(rA) < 1e-15 else "FAIL_CONTROL",
}

# ---- E01B: clean disjoint slots ----
fns = [clean] * 6
r = pluecker_residual(independent_brackets(fns, S0, T0, DS, DT))
mu, se = noise_standard_error(fns, S0, T0, DS, DT)
results["E01B_CLEAN_INDEPENDENT_SLOTS"] = {
    "raw_residual": r, "noise_standard_error": se, "z_score": r / se,
    "rejection_threshold": REJECTION_SIGMA, "status": verdict(r / se),
}


# ---- E01C: single-channel sensor gain is Pluecker-invisible ----
def vfault(s, T):
    x = channels(fresh, s, T)
    x[0] *= 1.02
    return x


fns = [clean, vfault, clean, vfault, clean, vfault]
r = pluecker_residual(independent_brackets(fns, S0, T0, DS, DT))
mu, se = noise_standard_error(fns, S0, T0, DS, DT)
results["E01C_SENSOR_GAIN_PLUECKER_INVISIBLE"] = {
    "gain_error": 0.02, "raw_residual": r, "z_score": r / se,
    "status": verdict(r / se),
    "note": "A gain error on ONE channel scales three brackets by the "
            "same factor; the Pfaffian scales and its zero is preserved. "
            "Single-channel gain faults are therefore OUTSIDE the "
            "Pluecker detection class -- a property of the theorem, "
            "stated openly and regression-tested. Rung E01E shows the "
            "cut-square localization catches exactly this fault class.",
}


# ---- E01D: aging ladder ----
def aging_slots(fade, gr, ea):
    return [(lambda s, T, m=CellModel(fade=fade * k / 5,
                                      r_grow=gr * k / 5,
                                      Ea_over_k=2500.0 + ea * k / 5):
             channels(m, s, T)) for k in range(6)]


for label, fade, gr, ea in (("MILD_0p2PC_FADE", 0.002, 0.005, 10.0),
                            ("MIDLIFE_10PC_FADE", 0.10, 0.30, 400.0),
                            ("END_OF_LIFE_20PC_FADE", 0.20, 0.60, 800.0)):
    fns = aging_slots(fade, gr, ea)
    r = pluecker_residual(independent_brackets(fns, S0, T0, DS, DT))
    mu, se = noise_standard_error(fns, S0, T0, DS, DT)
    results[f"E01D_AGING_{label}"] = {
        "fade": fade, "r_grow": gr, "Ea_shift_K": ea,
        "raw_residual": r, "noise_standard_error": se, "z_score": r / se,
        "rejection_threshold": REJECTION_SIGMA, "status": verdict(r / se),
    }

# bootstrap confirmation for the rejecting rung
rng = np.random.default_rng(11)
key = "E01D_AGING_END_OF_LIFE_20PC_FADE"
if results[key]["status"] == "FALSIFIED_MEASUREMENT_CONTRACT":
    from e01_core import CHANNEL_NOISE, N_REPLICATE_AVG
    eff = CHANNEL_NOISE / np.sqrt(N_REPLICATE_AVG)
    fns = aging_slots(0.20, 0.60, 800.0)
    draws = []
    for _ in range(2000):
        B = {}
        for (i, j), fn in zip(PAIRS, fns):
            def noisy(s, T, fn=fn):
                x = fn(s, T)
                return x + rng.normal(0.0, eff, size=x.shape)
            uu, vv = gradients(noisy, S0, T0, DS, DT)
            B[f"B{i+1}{j+1}"] = uu[i] * vv[j] - uu[j] * vv[i]
        draws.append(pluecker_residual(B))
    lo, hi = np.percentile(draws, [0.05, 99.95])
    results[key]["bootstrap"] = {
        "n_draws": 2000, "p999_interval": [float(lo), float(hi)],
        "zero_inside_99p9": bool(lo <= 0.0 <= hi),
    }

# ---- E01E: cut-square localization -- cell aging vs sensor fault ----
c = declared_decoder(fresh, S0, T0, DS, DT)


def ch1_share(led):
    ps = led["pair_squares"]
    t = sum(ps.values())
    return (ps["12"] + ps["13"] + ps["14"]) / t if t > 0 else 0.0


y_aged = response_event(CellModel(fade=0.20, r_grow=0.60, Ea_over_k=3300.0),
                        S0, T0, DS, DT)
y_inst = response_event(fresh, S0, T0, DS, DT).copy()
y_inst[0] *= 1.02
led_a, led_i = cut_square_ledger(c, y_aged), cut_square_ledger(c, y_inst)
y_ok = response_event(fresh, S0, T0, DS, DT)
led_ok = cut_square_ledger(c, y_ok)
results["E01E_CUT_SQUARE_LOCALIZATION"] = {
    "identity_max_rel_residual": max(
        abs(led_a["identity_residual_T31_rel"]),
        abs(led_i["identity_residual_T31_rel"]),
        abs(led_ok["identity_residual_T31_rel"])),
    "clean_transverse_share": led_ok["transverse_share"],
    "aged_cell": {"transverse_share": led_a["transverse_share"],
                  "channel1_pair_share": ch1_share(led_a)},
    "voltage_sensor_fault": {"transverse_share": led_i["transverse_share"],
                             "channel1_pair_share": ch1_share(led_i)},
    "status": "PASS_CONTROL"
    if led_ok["transverse_share"] < 1e-12
    and led_a["transverse_share"] > 1e-6
    and led_i["transverse_share"] > 1e-6
    and ch1_share(led_i) > 0.999 and ch1_share(led_a) < 0.9
    else "FAIL_CONTROL",
    "note": "Discriminant: a pure voltage-sense gain fault puts ALL "
            "transverse energy in the channel-1 pairs (share = 1.0); "
            "cell aging spreads it across the resistance and thermal "
            "pairs. 'Is it the cell or the sensor?' gets a certified, "
            "localized answer.",
}

results["_meta"] = {
    "chart": "(s, T): state of charge x temperature",
    "chart_point": {"s": S0, "T_K": T0},
    "stencil": {"ds": DS, "dT_K": DT},
    "framework_sources": [
        "arXiv:2603.20773 rank-2 area-bracket theorem",
        "Recognition-Kernel-Framework theorum/thermodynamics/10 T3.1/T4.1",
    ],
    "audit_discipline": "Thermodynamics-Reproducibility T01; Bio-tech B01/B02",
}
results["_pin"] = sha256_of({k: v for k, v in results.items() if k != "_pin"})

out = os.path.join(HERE, "..", "..", "results")
os.makedirs(out, exist_ok=True)
with open(os.path.join(out, "E01_CERTIFICATE.json"), "w") as f:
    json.dump(results, f, indent=2, sort_keys=True)

for k, vr in results.items():
    if k.startswith("_"):
        continue
    line = f"{k}: {vr['status']}"
    if "z_score" in vr:
        line += f"  z={vr['z_score']:+.1f}"
    print(line)
print("pin:", results["_pin"])
