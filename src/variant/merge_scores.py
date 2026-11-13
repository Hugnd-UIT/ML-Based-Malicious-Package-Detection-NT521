"""Pool the per-person scores of one F run (F1-F6 split over three people) and report FPR/recall.

Each person ran verify_nt230.sh on his own share, in his own VM, and got <TAG>_ben_scores.csv and <TAG>_mal_scores.csv
there. Pool those files; do NOT re-score on the host: src/variant/score_mal.py reads traces/<pkg>/*_install_log.txt,
which exists only in the VM, so a host re-score would drop malicious packages whose pip failed after the build stage ran.

  python3 src/variant/merge_scores.py --tag F1 --out results/nt230/F1 \
      results/nt230/F1/Hoang results/nt230/F1/Dang results/nt230/F1/Hung

Each folder holds the unpacked <TAG>_out.tar.gz of one person. Writes <out>/<TAG>_ben_scores.csv and
<out>/<TAG>_mal_scores.csv (input of src/variant/compare_runs.py) and prints, per person, how many runs were
excluded, then FPR / recall with Wilson 95% CI for the pooled valid runs.
"""
import argparse, os, sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from score import wilson

MODELS = ["RF_authors", "RF_drop_g1g2", "RF_drop_g1g2g3"]
SPREAD_HINT = 0.10  # hint only, not a protocol rule: exclusion rates of two people differ by 10 points or more


def read_class(tag, kind, dirs):
    parts = []
    for d in dirs:
        path = os.path.join(d, f"{tag}_{kind}_scores.csv")
        if not os.path.exists(path):
            sys.exit(f"missing {path}")
        df = pd.read_csv(path, keep_default_na=False)
        df["Person"] = os.path.basename(os.path.normpath(d))
        parts.append(df)
    pooled = pd.concat(parts, ignore_index=True)
    dup = pooled[pooled.duplicated("Package_Name", keep=False)]
    if len(dup):
        sys.exit(f"{kind}: package measured by more than one person (the three shares overlap):\n"
                 + dup[["Package_Name", "Person"]].to_string(index=False))
    return pooled


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dirs", nargs="+", help="one folder per person, each with <TAG>_ben_scores.csv and <TAG>_mal_scores.csv")
    ap.add_argument("--tag", required=True, help="run name, e.g. F1")
    ap.add_argument("--out", required=True, help="folder for the pooled <TAG>_ben_scores.csv and <TAG>_mal_scores.csv")
    a = ap.parse_args()

    pooled = {kind: read_class(a.tag, kind, a.dirs) for kind in ("ben", "mal")}  # read and check both before writing anything
    os.makedirs(a.out, exist_ok=True)
    for kind, what in (("ben", "FPR"), ("mal", "recall")):
        d = pooled[kind]
        d["Valid"] = d.Excluded.astype(str) == ""
        d.to_csv(os.path.join(a.out, f"{a.tag}_{kind}_scores.csv"), index=False)

        print(f"=== {a.tag} {'benign' if kind == 'ben' else 'malicious'}: runs and exclusions per person")
        rates = {}
        for person, g in d.groupby("Person", sort=False):
            rates[person] = 1 - g.Valid.mean()
            print(f"  {person:8s} traced {len(g):3d} | excluded {int((~g.Valid).sum()):3d} ({rates[person]:.1%})")
        if max(rates.values()) - min(rates.values()) >= SPREAD_HINT:
            print("  note: exclusion rates differ by 10 points or more between people; check the machines before trusting the pooled number")

        ok = d[d.Valid]
        print(f"  pooled valid {len(ok)} of {len(d)}")
        for m in MODELS:
            k = int((pd.to_numeric(ok[m]) >= 0.5).sum())  # flagged malicious: false positives on benign, hits on malicious
            lo, hi = wilson(k, len(ok))
            print(f"  {m:15s} {what} {k}/{len(ok)} = {k / max(len(ok), 1):.1%} (95% CI {lo:.1%}-{hi:.1%})")
    print(f"[+] {os.path.join(a.out, a.tag + '_ben_scores.csv')}, {os.path.join(a.out, a.tag + '_mal_scores.csv')}")


if __name__ == "__main__":
    main()
