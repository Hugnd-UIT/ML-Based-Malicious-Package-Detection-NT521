"""Compare the same packages traced under different settings (duration, network, cache, strace mode).

    python src/sensitivity.py runs/d60 runs/d120 runs/d300 [--model Random-Forest] [--out file.md]

Each run must already have features.csv and predictions.csv (python src/collect.py runs/<tag>).
For every package present in all runs it prints how the numeric features move and whether
the verdict of the model changes; a verdict that flips is exactly what the NT230 report asks for.
"""
import argparse, os, sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract import FEATURES
from preprocess import CAT_COLS

NUMERIC = [c for c in FEATURES if c not in CAT_COLS]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--model", default="Random-Forest")
    ap.add_argument("--threshold", type=float, default=0.2, help="relative change counted as 'changed'")
    ap.add_argument("--out")
    args = ap.parse_args()

    tags = [os.path.basename(r.rstrip("/\\")) for r in args.runs]
    feats = {t: pd.read_csv(os.path.join(r, "features.csv")).set_index("Package_Name") for t, r in zip(tags, args.runs)}
    preds = {}
    for t, r in zip(tags, args.runs):
        p = pd.read_csv(os.path.join(r, "predictions.csv"))
        preds[t] = p[p.Model == args.model].set_index("Package_Name")

    common = sorted(set.intersection(*(set(f.index) for f in feats.values())))
    ref = tags[0]
    lines = [f"# Sensitivity: {' vs '.join(tags)} (model {args.model})", "",
             f"Reference run: `{ref}`. 'Changed' = numeric feature moving more than {args.threshold:.0%}.", "",
             "| Package | Label | " + " | ".join(f"{t} pred (prob)" for t in tags) + " | Flip | Changed features |",
             "|---|---|" + "---|" * len(tags) + "---|---|"]
    flips = 0
    for pkg in common:
        cells = []
        verdicts = set()
        for t in tags:
            row = preds[t].loc[pkg]
            verdicts.add(int(row.Pred))
            prob = "" if pd.isna(row.Prob) else f" ({float(row.Prob):.2f})"
            cells.append(("MAL" if row.Pred == 1 else "ben") + prob)
        changed = []
        for c in NUMERIC:
            a = feats[ref].loc[pkg, c]
            for t in tags[1:]:
                b = feats[t].loc[pkg, c]
                if abs(b - a) > args.threshold * max(abs(a), 1):
                    changed.append(f"{c} {a}->{b}")
                    break
        flip = len(verdicts) > 1
        flips += flip
        label = feats[ref].loc[pkg].get("Level", "")
        label = "" if pd.isna(label) else int(label)
        lines.append(f"| {pkg} | {label} | " + " | ".join(cells) +
                     f" | {'**YES**' if flip else ''} | {'; '.join(changed[:6])}{' ...' if len(changed) > 6 else ''} |")

    lines += ["", f"{flips}/{len(common)} packages change verdict between runs."]
    text = "\n".join(lines)
    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")


if __name__ == "__main__":
    main()
