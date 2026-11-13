"""Paired comparison of two runs on the same packages (NT230: impact of OS, duration, dependency, sandbox).

  python3 src/variant/compare_runs.py --a F1_ben_scores.csv F1_mal_scores.csv --b F3_ben_scores.csv F3_mal_scores.csv \
      --name-a "mirror 120 s" --name-b "mirror 60 s"

Inputs are the *_scores.csv written by score_benign.py / score_mal.py (lap C/D/E and verify_nt230.sh).
Only packages valid (Excluded empty) in BOTH runs are counted. For each model: FPR on benign, recall on
malicious, each with a Wilson 95% CI, and an exact two-sided McNemar test on the packages whose verdict flips.
"""
import argparse, math, os, sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from score import wilson

MODELS = ["RF_authors", "RF_drop_g1g2", "RF_drop_g1g2g3"]


def read(files):
    parts = []
    for f in files:
        d = pd.read_csv(f, keep_default_na=False)
        d["Label"] = 0 if "_ben" in os.path.basename(f) else 1
        parts.append(d)
    d = pd.concat(parts).drop_duplicates("Package_Name", keep="last")
    return d[d.Excluded.astype(str) == ""].set_index("Package_Name")


def mcnemar(only_a, only_b):
    n, k = only_a + only_b, min(only_a, only_b)
    return min(1.0, 2 * sum(math.comb(n, j) for j in range(k + 1)) / 2 ** n) if n else 1.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", nargs="+", required=True, help="scores of run A (benign and/or malicious)")
    ap.add_argument("--b", nargs="+", required=True, help="scores of run B")
    ap.add_argument("--name-a", default="A")
    ap.add_argument("--name-b", default="B")
    ap.add_argument("--out", help="optional CSV with the paired per-package scores")
    x = ap.parse_args()
    a, b = read(x.a), read(x.b)
    both = a.index.intersection(b.index)
    a, b = a.loc[both], b.loc[both]
    print(f"paired valid packages: {len(both)} (benign {int((a.Label == 0).sum())}, malicious {int((a.Label == 1).sum())})")
    for label, what in ((0, "FPR"), (1, "recall")):
        sel = a.Label == label
        n = int(sel.sum())
        if not n:
            continue
        print(f"--- {'benign' if label == 0 else 'malicious'} ({what}), n={n}")
        for m in MODELS:
            if m not in a or m not in b:
                continue
            fa = pd.to_numeric(a.loc[sel, m]) >= 0.5
            fb = pd.to_numeric(b.loc[sel, m]) >= 0.5
            ka, kb = int(fa.sum()), int(fb.sum())
            la, ha = wilson(ka, n)
            lb, hb = wilson(kb, n)
            only_a, only_b = int((fa & ~fb).sum()), int((~fa & fb).sum())
            shift = (pd.to_numeric(b.loc[sel, m]) - pd.to_numeric(a.loc[sel, m])).median()
            print(f"  {m:15s} {x.name_a}: {ka}/{n} = {ka / n:.1%} ({la:.1%}-{ha:.1%}) | {x.name_b}: {kb}/{n} = {kb / n:.1%} "
                  f"({lb:.1%}-{hb:.1%}) | flips {only_a} -> {only_b}, McNemar p = {mcnemar(only_a, only_b):.4f} | "
                  f"median score change {shift:+.3f}")
    if x.out:
        cols = [m for m in MODELS if m in a and m in b]
        out = a[["Label"] + cols].join(b[cols], lsuffix="_" + x.name_a, rsuffix="_" + x.name_b)
        out.to_csv(x.out)
        print(f"[+] {x.out}")


if __name__ == "__main__":
    main()
