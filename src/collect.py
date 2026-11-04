"""Turn one trace run (runs/<tag>/) into features, predictions and cost tables.

    python src/collect.py runs/<tag>

Writes into runs/<tag>/:
    features.csv     Package_Name + 36 features + Level + Group  (cross-dataset test set for Hung)
    predictions.csv  one row per package x model: pred, prob, correct
    errors.csv       only the wrong predictions (FP/FN) for the error taxonomy
    cost.csv         install/trace time, log size, extraction time, predict latency
"""
import argparse, csv, os, sys, time
import joblib
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract import FEATURES, extract, packages
from preprocess import transform

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_MODELS = os.path.join(BASE, "models")
# 4 models of the DySec paper; --extra adds the NT230 baselines (Dummy, LR, KNN).
PAPER = ["Random-Forest", "Decision-Tree", "Gradient-Boosting", "SVM"]
EXTRA = ["Dummy-Classifier", "Logistic-Regression", "KNN"]
NAMES = PAPER + EXTRA if "--extra" in sys.argv else PAPER


def read_list(run):
    path = os.path.join(run, "packages.csv")
    if not os.path.exists(path):
        path = os.path.join(BASE, "dataset", "our-traces", "packages.csv")
    with open(path, encoding="utf-8") as f:
        return {r["name"]: r for r in csv.DictReader(f)}


def read_meta(run, pkg):
    meta = {}
    path = os.path.join(run, "traces", pkg, "meta.env")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                k, _, v = line.rstrip("\n").partition("=")
                meta[k] = v
    return meta


def size(path):
    total = 0
    for root, _, files in os.walk(path):
        total += sum(os.path.getsize(os.path.join(root, f)) for f in files)
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", help="run folder containing traces/ and outputs/")
    ap.add_argument("--all-procs", action="store_true",
                    help="count syscalls of every traced process (children too); output files get the suffix _allproc")
    ap.add_argument("--extra", action="store_true",
                    help="also run the NT230 baselines (Dummy, LR, KNN); not part of the paper")
    args = ap.parse_args()
    run = args.run.rstrip("/\\")
    suffix = ""
    if args.all_procs:
        os.environ["DYSEC_ALL_PROCS"] = "1"
        suffix = "_allproc"

    labels = read_list(run)
    models = {n: joblib.load(os.path.join(DIR_MODELS, f"{n}.pkl"))
              for n in NAMES if os.path.exists(os.path.join(DIR_MODELS, f"{n}.pkl"))}

    feats, preds, costs, skipped = [], [], [], []
    for pkg in packages(run, "ours"):
        meta = read_meta(run, pkg)
        log = os.path.join(run, "traces", pkg, f"{pkg}_install_log.txt")
        text = open(log, encoding="utf-8", errors="replace").read() if os.path.exists(log) else ""
        if meta.get("result", "Success") != "Success":
            skipped.append((pkg, "install failed"))
            continue
        if text and "Successfully installed" not in text:
            skipped.append((pkg, "nothing was installed (already satisfied)"))
            continue
        info = labels.get(pkg, {})
        level = int(info["label"]) if info.get("label", "") != "" else None

        t0 = time.perf_counter()
        row = extract(run, pkg)
        t_extract = time.perf_counter() - t0
        row["Level"] = level
        row["Group"] = info.get("group", "")
        feats.append(row)

        t0 = time.perf_counter()
        X = transform(pd.DataFrame([row]))
        t_transform = time.perf_counter() - t0
        latency = {}
        for name, model in models.items():
            t0 = time.perf_counter()
            pred = int(model.predict(X)[0])
            try:
                prob = round(float(model.predict_proba(X)[0][1]), 4)
            except Exception:
                prob = ""
            latency[name] = time.perf_counter() - t0
            preds.append({"Package_Name": pkg, "Group": row["Group"], "Level": level, "Model": name,
                          "Pred": pred, "Prob": prob,
                          "Correct": "" if level is None else int(pred == level)})

        meta = read_meta(run, pkg)
        costs.append({
            "Package_Name": pkg,
            "install_seconds": meta.get("install_seconds", ""),
            "trace_seconds": meta.get("trace_seconds", ""),
            "ebpf_MB": round(size(os.path.join(run, "traces", pkg)) / 2**20, 2),
            "strace_MB": round(size(os.path.join(run, "outputs", pkg)) / 2**20 +
                               size(os.path.join(run, "Trace_Outputs", pkg)) / 2**20, 2),
            "extract_seconds": round(t_extract, 3),
            "transform_ms": round(t_transform * 1000, 2),
            "rf_predict_ms": round(latency.get("Random-Forest", 0) * 1000, 2),
            "max_predict_ms": round(max(latency.values(), default=0) * 1000, 2),
            "netmode": meta.get("netmode", ""), "strace": meta.get("strace", ""),
            "duration": meta.get("duration", ""), "pipcache": meta.get("pipcache", ""),
        })

    cols = ["Package_Name"] + FEATURES + ["Level", "Group"]
    pd.DataFrame(feats)[cols].to_csv(os.path.join(run, "features" + suffix + ".csv"), index=False)
    p = pd.DataFrame(preds)
    p.to_csv(os.path.join(run, "predictions" + suffix + ".csv"), index=False)
    p[p.Correct == 0].to_csv(os.path.join(run, "errors" + suffix + ".csv"), index=False)
    pd.DataFrame(costs).to_csv(os.path.join(run, "cost" + suffix + ".csv"), index=False)

    # Short summary on screen: prediction of every model for every package.
    wide = p.pivot(index="Package_Name", columns="Model", values="Pred")
    wide = wide[[n for n in NAMES if n in wide.columns]]
    wide.columns = [c.split("-")[0][:6] for c in wide.columns]
    meta = p.drop_duplicates("Package_Name").set_index("Package_Name")[["Group", "Level"]]
    print(meta.join(wide).to_string())
    known = p[p.Correct != ""]
    if len(known):
        acc = known.assign(Correct=known.Correct.astype(int)).groupby("Model").Correct.mean()
        print("\nAccuracy on this run:", {k: round(v, 3) for k, v in acc.items()})
    for pkg, why in skipped:
        print(f"[!] skipped {pkg}: {why}")
    print(f"\n[+] {len(feats)} packages -> {run}/features{suffix}.csv, predictions{suffix}.csv, errors{suffix}.csv, cost{suffix}.csv")


if __name__ == "__main__":
    main()
