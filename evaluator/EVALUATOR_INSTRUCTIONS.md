# Independent evaluator instructions — Energy E01-EXP-3

You are being asked to independently verify one claim: that the
preregistered statistic of campaign E01-EXP-3, recomputed by you from
the pinned public raw data, reproduces the committed certificate
(`results/E01_EXP3_CERTIFICATE.json`: CERTIFIED_AGING_TREND on six
CALCE CS2 cells, Fisher X = 75.4, combined p = 3.1e-11).

You do not need to trust the developer. Everything you run is in this
repository; every input is hash-pinned; the statistic and its
threshold were committed (git history: `E01_EXP3_PREREGISTRATION.md`)
before the data was downloaded.

## Steps

1. Fresh clone of https://github.com/Parveen117/Energy. Install:
   `python -m pip install numpy scipy pandas openpyxl cryptography`.
2. Download the six `CS2_3x.zip` assets from the repository release
   `raw-data-v1` into `data/raw/` (browser is fine).
3. `python evaluator/run_evaluation.py check`
   — verifies every raw-file hash against `data/MANIFEST.sha256` and
   every pinned certificate plus the canonical results root. Must
   print `CHECK: PASS` before you continue.
4. `python evaluator/run_evaluation.py reproduce`
   — extracts the pinned archives and re-runs the preregistered
   pipeline. Must end with `VERDICT: REPRODUCED` (byte-identical pin).
   `MISMATCH` is a reportable finding: publish it.
5. `python evaluator/run_evaluation.py keygen` then `... sign`
   — signs your `evaluator/EVALUATION_CERTIFICATE.json` with your own
   Ed25519 key. Send the signed JSON (it embeds your public key) back,
   or publish it anywhere you like; anyone can check it with
   `... verify-cert`.

## What your signature means

Only this: on your machine, from the pinned inputs, the committed
statistic recomputed to the committed value. It does not endorse the
framework, the interpretation, or any product claim. Your name/key is
credited in the repository unless you prefer otherwise.
