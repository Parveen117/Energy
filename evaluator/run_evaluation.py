"""Independent evaluation of the Energy flagship certificate (E01-EXP-3).

For an evaluator who is NOT the developer. One command per step:

  python evaluator/run_evaluation.py check     # verify data pins + certs
  python evaluator/run_evaluation.py reproduce # recompute EXP-3 from raw
  python evaluator/run_evaluation.py keygen    # make an Ed25519 keypair
  python evaluator/run_evaluation.py sign      # sign the verdict
  python evaluator/run_evaluation.py verify-cert EVALUATION_CERTIFICATE.json

`reproduce` re-runs the preregistered EXP-3 pipeline from the pinned
raw archives in a fresh checkout and compares the recomputed statistic
and pin against the committed certificate. The evaluation verdict is
REPRODUCED only if the recomputed pin matches byte-for-byte.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RES = os.path.join(ROOT, "results")
KEYDIR = os.path.join(os.path.dirname(__file__), "keys")


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def check():
    bad = []
    for line in open(os.path.join(ROOT, "data", "MANIFEST.sha256")):
        if not line.strip():
            continue
        h, rel = line.strip().split(maxsplit=1)
        p = os.path.join(ROOT, "data", rel)
        if not os.path.exists(p):
            bad.append(f"missing {rel}")
        elif sha_file(p) != h:
            bad.append(f"hash mismatch {rel}")
    r = subprocess.run([sys.executable,
                        os.path.join(ROOT, "scripts",
                                     "verify_certificates.py")])
    ok = not bad and r.returncode == 0
    for b in bad:
        print("BAD", b)
    print("CHECK:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def reproduce():
    cert = json.load(open(os.path.join(RES, "E01_EXP3_CERTIFICATE.json")))
    pinned = cert["_pin"]
    ex = os.path.join(ROOT, "data", "extracted")
    if not os.path.isdir(os.path.join(ex, "CS2_33")):
        os.makedirs(ex, exist_ok=True)
        import zipfile
        for i in range(33, 39):
            with zipfile.ZipFile(os.path.join(
                    ROOT, "data", "raw", f"CS2_{i}.zip")) as z:
                z.extractall(ex)
    r = subprocess.run([sys.executable, os.path.join(
        ROOT, "campaigns", "E01_CELL_CHART_AUDIT", "run_e01_exp3.py")],
        capture_output=True, text=True)
    print(r.stdout[-800:])
    fresh = json.load(open(os.path.join(RES, "E01_EXP3_CERTIFICATE.json")))
    verdict = "REPRODUCED" if fresh["_pin"] == pinned else "MISMATCH"
    out = {
        "evaluated_certificate": "E01_EXP3_CERTIFICATE.json",
        "pinned_pin": pinned, "recomputed_pin": fresh["_pin"],
        "combined_p": fresh["combined_p"], "verdict": verdict,
        "note": "REPRODUCED means the preregistered statistic recomputed "
                "from the pinned raw archives matches the committed "
                "certificate byte-for-byte.",
    }
    json.dump(out, open(os.path.join(
        os.path.dirname(__file__), "EVALUATION_CERTIFICATE.json"), "w"),
        indent=2, sort_keys=True)
    print("VERDICT:", verdict)
    return 0 if verdict == "REPRODUCED" else 1


def keygen():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import \
        Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization as s
    os.makedirs(KEYDIR, exist_ok=True)
    k = Ed25519PrivateKey.generate()
    open(os.path.join(KEYDIR, "evaluator_private.pem"), "wb").write(
        k.private_bytes(s.Encoding.PEM, s.PrivateFormat.PKCS8,
                        s.NoEncryption()))
    open(os.path.join(KEYDIR, "evaluator_public.pem"), "wb").write(
        k.public_key().public_bytes(s.Encoding.PEM,
                                    s.PublicFormat.SubjectPublicKeyInfo))
    os.chmod(os.path.join(KEYDIR, "evaluator_private.pem"), 0o600)
    print("keys written to evaluator/keys/")
    return 0


def sign():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import \
        Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization as s
    cert_p = os.path.join(os.path.dirname(__file__),
                          "EVALUATION_CERTIFICATE.json")
    body = open(cert_p, "rb").read()
    key = s.load_pem_private_key(
        open(os.path.join(KEYDIR, "evaluator_private.pem"), "rb").read(),
        password=None)
    sig = key.sign(body).hex()
    cert = json.loads(body)
    cert["ed25519_signature_hex"] = sig
    cert["public_key_pem"] = open(
        os.path.join(KEYDIR, "evaluator_public.pem")).read()
    json.dump(cert, open(cert_p, "w"), indent=2, sort_keys=True)
    print("signed EVALUATION_CERTIFICATE.json")
    return 0


def verify_cert(path):
    from cryptography.hazmat.primitives import serialization as s
    cert = json.load(open(path))
    sig = bytes.fromhex(cert.pop("ed25519_signature_hex"))
    pub = s.load_pem_public_key(cert.pop("public_key_pem").encode())
    body = json.dumps(cert, indent=2, sort_keys=True).encode()
    try:
        pub.verify(sig, body)
        print("SIGNATURE VALID; verdict:", cert["verdict"])
        return 0
    except Exception:
        print("SIGNATURE INVALID")
        return 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "check":
        sys.exit(check())
    if cmd == "reproduce":
        sys.exit(reproduce())
    if cmd == "keygen":
        sys.exit(keygen())
    if cmd == "sign":
        sys.exit(sign())
    if cmd == "verify-cert":
        sys.exit(verify_cert(sys.argv[2]))
    print(__doc__)
