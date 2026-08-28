import json
import os
import subprocess
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAMP = os.path.join(ROOT, "campaigns", "E01_CELL_CHART_AUDIT")
sys.path.insert(0, CAMP)

from e01_core import (CellModel, brackets_common, channels,
                      cut_square_ledger, declared_decoder, gradients,
                      independent_brackets, pluecker_residual,
                      response_event)

S0, T0, DS, DT = 0.5, 298.15, 0.05, 5.0
FRESH = CellModel()


def clean(s, T):
    return channels(FRESH, s, T)


def test_common_gradient_identity():
    u, v = gradients(clean, S0, T0, DS, DT)
    assert abs(pluecker_residual(brackets_common(u, v))) < 1e-15


def test_channels_span_chart():
    u, v = gradients(clean, S0, T0, DS, DT)
    s = np.linalg.svd(np.stack([u, v]), compute_uv=False)
    assert s[1] / s[0] > 1e-3


def test_single_channel_gain_is_pluecker_invisible():
    # theorem property: gain on one channel scales the Pfaffian, so its
    # zero is preserved exactly.
    def vfault(s, T):
        x = channels(FRESH, s, T)
        x[0] *= 1.37
        return x
    fns = [clean, vfault, clean, vfault, clean, vfault]
    assert abs(pluecker_residual(
        independent_brackets(fns, S0, T0, DS, DT))) < 1e-15


def test_aging_moves_residual():
    fns = [(lambda s, T, m=CellModel(fade=0.20 * k / 5, r_grow=0.60 * k / 5,
                                     Ea_over_k=2500 + 800 * k / 5):
            channels(m, s, T)) for k in range(6)]
    assert abs(pluecker_residual(
        independent_brackets(fns, S0, T0, DS, DT))) > 1e-8


def test_cut_square_identity_and_discriminant():
    c = declared_decoder(FRESH, S0, T0, DS, DT)
    y_inst = response_event(FRESH, S0, T0, DS, DT).copy()
    y_inst[0] *= 1.02
    led = cut_square_ledger(c, y_inst)
    assert abs(led["identity_residual_T31_rel"]) < 1e-12
    ps = led["pair_squares"]
    ch1 = (ps["12"] + ps["13"] + ps["14"]) / sum(ps.values())
    assert ch1 > 0.999
    y_aged = response_event(CellModel(fade=0.20, r_grow=0.60,
                                      Ea_over_k=3300.0), S0, T0, DS, DT)
    led2 = cut_square_ledger(c, y_aged)
    ps2 = led2["pair_squares"]
    ch1b = (ps2["12"] + ps2["13"] + ps2["14"]) / sum(ps2.values())
    assert ch1b < 0.9


def test_certificate_pin_reproduces():
    r = subprocess.run([sys.executable, os.path.join(CAMP, "run_e01.py")],
                       capture_output=True, text=True, check=True)
    with open(os.path.join(ROOT, "results", "E01_CERTIFICATE.json")) as f:
        cert = json.load(f)
    assert cert["_pin"] in r.stdout
    assert cert["E01D_AGING_END_OF_LIFE_20PC_FADE"]["status"] == \
        "FALSIFIED_MEASUREMENT_CONTRACT"
    assert cert["E01D_AGING_MILD_0p2PC_FADE"]["status"] == "NOT_FALSIFIED"
    assert cert["E01E_CUT_SQUARE_LOCALIZATION"]["status"] == "PASS_CONTROL"
