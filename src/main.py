import argparse, os, sys, subprocess
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract import extract, FEATURES
from predict import load_models, predict_pkg, show

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(BASE, "src", "scripts", "trace.sh")


def trace(pkg, duration):
    cmd = ["bash", SCRIPT, pkg, str(duration)]
    res = subprocess.run(cmd, cwd=BASE)
    return res.returncode == 0


def save(row, path):
    cols = ["Package_Name"] + FEATURES
    pd.DataFrame([row])[cols].to_csv(path, index=False)


def run(pkg, duration, out, skip):
    if not skip:
        if os.name != "nt" and os.geteuid() != 0:
            print("Error: Must run with sudo to capture eBPF traces.")
            sys.exit(1)
        ok = trace(pkg, duration)
        if not ok:
            print("Error: Trace failed.")
            sys.exit(1)

    row = extract(BASE, pkg)
    save(row, out)
    print(f"\n[+] Saved evidence: {out}\n")

    models = load_models()
    if not models:
        print("Error: No models found.")
        sys.exit(1)

    df = pd.DataFrame([row])
    results = predict_pkg(df, models)
    show(pkg, results)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pkg", help="package name or tar.gz file")
    ap.add_argument("duration", nargs="?", type=int, default=30, help="seconds to monitor")
    ap.add_argument("--out", help="output CSV evidence path")
    ap.add_argument("--skip", action="store_true", help="skip trace step")
    args = ap.parse_args()

    clean = os.path.basename(args.pkg).replace(".tar.gz", "").replace(".zip", "")
    out = args.out or f"{clean}_evidence.csv"
    run(args.pkg, args.duration, out, args.skip)


if __name__ == "__main__":
    main()
