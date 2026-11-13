"""Fixed subset for the NT230 sensitivity runs (F2-F6), written before any of those runs.

Source: data/mix-lapE.txt (270 packages of lap E / run F1). Rule: 50 benign and 50 malicious lines chosen with
random seed 230, kept in their lap E order, so every sensitivity run can be paired with F1 on the same packages.
  python3 src/data/make-mix-sens.py [n_per_class=50]  -> data/mix-sens.txt
"""
import os, random, sys

D = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
n = int(sys.argv[1]) if len(sys.argv) > 1 else 50
lines = [l.strip() for l in open(os.path.join(D, "mix-lapE.txt")) if l.strip()]
rng = random.Random(230)
keep = set()
for kind in ("B", "M"):
    keep |= set(rng.sample([l for l in lines if l.startswith(kind + " ")], n))
with open(os.path.join(D, "mix-sens.txt"), "w", newline="\n") as f:
    f.writelines(l + "\n" for l in lines if l in keep)
print(f"data/mix-sens.txt: {len(keep)} lines")
