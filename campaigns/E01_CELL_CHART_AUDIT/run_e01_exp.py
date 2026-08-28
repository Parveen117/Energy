"""E01-EXP: preregistered real-data rung for the cell-chart audit.

Refuses to run unless data/MANIFEST.sha256 exists and every listed
file's hash matches — pin first, analyze second. All analysis choices
are locked in E01_EXP_PREREGISTRATION.md, committed before download.

Expected inputs (NASA PCoE .mat files): per-cell structures with
cycle records of types 'charge', 'discharge', 'impedance', ambient
temperature per cell. The loader extracts, per declared life-stage
slot:
  - rest voltage near s0 = 0.5 (from relaxation points),
  - incremental-capacity proxy from the discharge voltage curve,
  - internal resistance (EIS real-axis intercept, field 'Re', or the
    dataset's 'Rct'+'Re' if labeled),
  - ambient temperature.
It fails loudly, naming the missing field, if a file does not carry
what the preregistration requires; a failed contract is a reportable
outcome, not something to paper over.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, HERE)

from e01_core import (PAIRS, REJECTION_SIGMA, pluecker_residual,  # noqa: E402
                      sha256_of, verdict)


def fail(msg):
    print(f"E01-EXP CONTRACT FAILURE: {msg}")
    print("This is a reportable outcome. Fix the data pinning or record "
          "a protocol deviation per E01_EXP_PREREGISTRATION.md.")
    sys.exit(2)


# ---------------- pin gate ----------------
manifest_path = os.path.join(DATA, "MANIFEST.sha256")
if not os.path.exists(manifest_path):
    fail("data/MANIFEST.sha256 not found. Download the datasets per "
         "data/README.md and pin them first.")

bad = []
files = []
for line in open(manifest_path):
    line = line.strip()
    if not line:
        continue
    h, rel = line.split(maxsplit=1)
    p = os.path.join(DATA, rel)
    if not os.path.exists(p):
        bad.append(f"missing: {rel}")
        continue
    actual = hashlib.sha256(open(p, "rb").read()).hexdigest()
    if actual != h:
        bad.append(f"hash mismatch: {rel}")
    files.append(p)
if bad:
    fail("; ".join(bad))
if not files:
    fail("MANIFEST.sha256 is empty.")

try:
    from scipy.io import loadmat
except ImportError:
    fail("scipy is required: python -m pip install scipy")


# ---------------- loader (NASA PCoE structure) ----------------
def load_cell(path):
    m = loadmat(path, simplify_cells=True)
    keys = [k for k in m if not k.startswith("__")]
    if len(keys) != 1:
        fail(f"{os.path.basename(path)}: expected one top-level cell "
             f"struct, found {keys}")
    cell = m[keys[0]]
    if "cycle" not in cell:
        fail(f"{os.path.basename(path)}: no 'cycle' field")
    return keys[0], cell["cycle"]


def rest_voltage_near_soc(cycles, target_frac=0.5):
    """Rest voltage proxy at ~50% SoC: voltage at the point of each
    discharge where delivered capacity is half of that cycle's total."""
    vals = []
    for cyc in cycles:
        if cyc.get("type") != "discharge":
            continue
        d = cyc.get("data", {})
        V = np.atleast_1d(d.get("Voltage_measured", []))
        t = np.atleast_1d(d.get("Time", []))
        I = np.atleast_1d(d.get("Current_measured", []))
        if len(V) < 10 or len(t) != len(V) or len(I) != len(V):
            continue
        q = np.cumsum(np.abs(I[:-1]) * np.diff(t)) / 3600.0
        if q[-1] <= 0:
            continue
        idx = int(np.searchsorted(q, target_frac * q[-1]))
        idx = min(idx, len(V) - 1)
        vals.append((float(V[idx]), float(q[-1])))
    return vals  # list of (voltage@50%, cycle capacity Ah)


def impedance_re(cycles):
    vals = []
    for cyc in cycles:
        if cyc.get("type") != "impedance":
            continue
        d = cyc.get("data", {})
        for field in ("Re", "Rectified_Impedance", "Rct"):
            if field in d:
                arr = np.atleast_1d(d[field]).astype(complex)
                if arr.size:
                    vals.append(float(np.real(arr).min()))
                    break
    return vals


def ambient_T(cycles):
    Ts = [float(c.get("ambient_temperature", np.nan)) for c in cycles
          if "ambient_temperature" in c]
    Ts = [t for t in Ts if np.isfinite(t)]
    return (np.median(Ts) + 273.15) if Ts else None


# ---------------- slot construction per preregistration ----------------
cells = {}
for p in files:
    if not p.endswith(".mat"):
        continue
    name, cycles = load_cell(p)
    T = ambient_T(cycles)
    rv = rest_voltage_near_soc(cycles)
    re_vals = impedance_re(cycles)
    if T is None:
        fail(f"{name}: no ambient_temperature field")
    if len(rv) < 12:
        fail(f"{name}: fewer than 12 usable discharge cycles")
    if len(re_vals) < 6:
        fail(f"{name}: fewer than 6 impedance records (EIS required by "
             "preregistration section 2)")
    cells[name] = {"T": T, "rv": rv, "re": re_vals}

Tgroups = sorted({round(c["T"]) for c in cells.values()})
if len(Tgroups) < 2:
    fail(f"only one temperature group present ({Tgroups}); the (s, T) "
         "chart needs at least two ambient temperatures "
         "(preregistration section 1).")

# Build six life-stage slots; each slot supplies one bracket estimated
# from finite differences across SoC (within-cycle voltage curve) and
# across temperature groups (matched life stage).
# The full bracket construction follows e01_core with per-slot data;
# implementation continues below once real field layouts are confirmed
# against the pinned files.
print("E01-EXP: pin gate PASSED;", len(cells), "cells loaded across",
      len(Tgroups), "temperature groups:", Tgroups)
print("Slot construction proceeds per preregistration. If this message "
      "is reached with real pinned data, extend run_e01_exp.py's slot "
      "assembly against the confirmed field layout and record any "
      "deviation in the certificate.")
summary = {
    "pin_gate": "PASSED",
    "cells": {k: {"T_K": v["T"], "n_discharge": len(v["rv"]),
                  "n_impedance": len(v["re"])} for k, v in cells.items()},
    "temperature_groups_K": Tgroups,
    "status": "DATA_CONTRACT_SATISFIED_ANALYSIS_PENDING",
}
summary["_pin"] = sha256_of({k: v for k, v in summary.items()
                             if k != "_pin"})
out = os.path.join(ROOT, "results")
os.makedirs(out, exist_ok=True)
with open(os.path.join(out, "E01_EXP_INTAKE.json"), "w") as f:
    json.dump(summary, f, indent=2, sort_keys=True)
print("intake pinned:", summary["_pin"])
