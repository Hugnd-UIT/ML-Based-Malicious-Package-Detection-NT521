import argparse, os, sys, joblib
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from preprocess import transform

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_MODELS = os.path.join(BASE, "models")
NAMES = ["Random-Forest", "Decision-Tree", "Gradient-Boosting", "SVM", "Logistic-Regression", "KNN"]


def load_models():
    models = {}
    for name in NAMES:
        path = os.path.join(DIR_MODELS, f"{name}.pkl")
        if os.path.exists(path):
            models[name] = joblib.load(path)
    return models


def predict_pkg(df, models):
    X = transform(df)
    results = []
    for name, model in models.items():
        pred = int(model.predict(X)[0])
        label = "MALICIOUS" if pred == 1 else "BENIGN"
        prob = None
        if hasattr(model, "predict_proba"):
            try:
                prob = float(model.predict_proba(X)[0][1])
            except Exception:
                prob = None
        results.append({"model": name, "pred": pred, "label": label, "prob": prob})
    return results


def show(pkg, results):
    print("=" * 64)
    print(f"PACKAGE: {pkg}")
    print("=" * 64)
    print(f"{'Model':<21}{'Prediction':<16}Probability")
    print("-" * 64)
    for r in results:
        prob = f"{r['prob'] * 100:>7.2f}%" if r["prob"] is not None else "    N/A"
        print(f"{r['model']:<21}{r['label']:<16}  {prob}")
    print("=" * 64 + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", nargs="?", help="path to extracted CSV file")
    ap.add_argument("--csv", help="path to extracted CSV file")
    args = ap.parse_args()

    csv_path = args.input or args.csv
    if not csv_path or not os.path.exists(csv_path):
        print("Usage: python src/predict.py <path_to_extracted.csv>")
        return

    models = load_models()
    if not models:
        print("Error: No models found in models/ directory.")
        return

    df = pd.read_csv(csv_path)
    for _, row in df.iterrows():
        pkg = row.get("Package_Name", "Unknown")
        row_df = pd.DataFrame([row])
        res = predict_pkg(row_df, models)
        show(pkg, res)


if __name__ == "__main__":
    main()
