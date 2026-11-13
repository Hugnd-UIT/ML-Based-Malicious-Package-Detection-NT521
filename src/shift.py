"""Explain why packages traced by us are classified differently from QUT-DV25 (distribution shift).

    python src/shift.py results/runs/<tag>/features.csv [--pkg requests] [--out file.md]

For every package:
  * unseen  : categorical columns whose text never appears in train.csv (encoded as -1)
  * outside : numeric features outside the 5-95 percentile range of QUT-DV25 benign packages
  * what-if : how the Random-Forest probability moves when one feature is reset to a typical
              benign value; the biggest moves are the features that drive the verdict.
"""
import argparse, os, sys
import joblib
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract import FEATURES
from preprocess import CAT_COLS, transform

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NUMERIC = [c for c in FEATURES if c not in CAT_COLS]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("features")
    ap.add_argument("--pkg", nargs="*")
    ap.add_argument("--model", default="Random-Forest")
    ap.add_argument("--out")
    args = ap.parse_args()

    train = pd.read_csv(os.path.join(BASE, "dataset", "train.csv"))
    benign = train[train.Level == 0]
    Xb = transform(benign)
    typical = {c: Xb[c].median() for c in NUMERIC}
    typical.update({c: Xb[c].mode()[0] for c in CAT_COLS})
    lo, hi = benign[NUMERIC].quantile(0.05), benign[NUMERIC].quantile(0.95)
    model = joblib.load(os.path.join(BASE, "models", f"{args.model}.pkl"))

    ours = pd.read_csv(args.features)
    if args.pkg:
        ours = ours[ours.Package_Name.isin(args.pkg)]
    X = transform(ours)

    lines = [f"# Distribution shift vs QUT-DV25 ({args.model})", "",
             "| Package | Label | P(mal) | Unseen text cols | Numeric outside benign p5-p95 | Biggest what-if moves |",
             "|---|---|---|---|---|---|"]
    for i, pkg in enumerate(ours.Package_Name):
        x = X.iloc[[i]]
        p0 = float(model.predict_proba(x)[0][1])
        unseen = [c for c in CAT_COLS if x[c].iloc[0] == -1]
        outside = [f"{c}={int(ours.iloc[i][c])} ({int(lo[c])}-{int(hi[c])})"
                   for c in NUMERIC if not lo[c] <= ours.iloc[i][c] <= hi[c]]
        moves = []
        for c in FEATURES:
            x2 = x.copy()
            x2[c] = typical[c]
            d = float(model.predict_proba(x2)[0][1]) - p0
            if abs(d) >= 0.05:
                moves.append((d, c))
        moves = [f"{c} {d:+.2f}" for d, c in sorted(moves)[:4]]
        label = ours.iloc[i].get("Level", "")
        label = "" if pd.isna(label) else int(label)
        lines.append(f"| {pkg} | {label} | {p0:.2f} | {len(unseen)}/19: {', '.join(unseen)} | "
                     f"{'; '.join(outside)} | {'; '.join(moves)} |")

    text = "\n".join(lines)
    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")


if __name__ == "__main__":
    main()
