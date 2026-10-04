import os
import numpy as np
import pandas as pd

base = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(base, 'QUT-DV25.csv')


def load_data():
    return pd.read_csv(path)


def analyze_label(data):
    total = len(data)
    zero_cnt = (data['Level'] == 0).sum()
    one_cnt = (data['Level'] == 1).sum()
    return {
        'total': total,
        'benign': zero_cnt,
        'malicious': one_cnt,
        'benign_pct': round(zero_cnt / total * 100, 2),
        'malicious_pct': round(one_cnt / total * 100, 2)
    }


def analyze_quality(data):
    null_sum = int(data.isnull().sum().sum())
    dup_rows = int(data.duplicated().sum())
    feat_cols = [c for c in data.columns if c not in ('Package_Name', 'Level')]
    dup_feats = int(data.duplicated(subset=feat_cols).sum())
    return {
        'nulls': null_sum,
        'duplicate_rows': dup_rows,
        'duplicate_features': dup_feats
    }


def analyze_constant(data):
    feat_cols = [c for c in data.columns if c not in ('Package_Name', 'Level')]
    constants = []
    near_constants = []
    total = len(data)
    for col in feat_cols:
        uniq = data[col].nunique()
        if uniq <= 1:
            constants.append(col)
        else:
            top_freq = data[col].value_counts(normalize=True).iloc[0]
            if top_freq >= 0.99:
                near_constants.append((col, round(top_freq * 100, 2)))
    return constants, near_constants


def analyze_correlation(data):
    feat_cols = [c for c in data.columns if c not in ('Package_Name', 'Level')]
    temp = data.copy()
    for col in feat_cols:
        if temp[col].dtype == 'object' or pd.api.types.is_string_dtype(temp[col]):
            temp[col] = pd.factorize(temp[col])[0]
    corrs = {}
    for col in feat_cols:
        val = temp[col].corr(temp['Level'])
        corrs[col] = round(float(val), 4)
    sorted_corrs = sorted(corrs.items(), key=lambda x: abs(x[1]), reverse=True)
    return sorted_corrs


def run():
    data = load_data()
    labels = analyze_label(data)
    quality = analyze_quality(data)
    constants, near_constants = analyze_constant(data)
    correlations = analyze_correlation(data)

    print("=== LABELs ===")
    print(f"Total: {labels['total']:,}")
    print(f"Benign: {labels['benign']:,} ({labels['benign_pct']}%)")
    print(f"Malicious: {labels['malicious']:,} ({labels['malicious_pct']}%)")

    print("\n=== QUALITY ===")
    print(f"Null values: {quality['nulls']}")
    print(f"Duplicate full rows: {quality['duplicate_rows']}")
    print(f"Duplicate feature rows: {quality['duplicate_features']}")

    print("\n=== CONSTANTS ===")
    print(f"Zero variance: {constants if constants else 'None'}")
    print(f"Near-constant: {len(near_constants)}")
    for col, pct in near_constants:
        print(f"- {col}: {pct}%")

    print("\n=== CORRELATIONS ===")
    for col, corr in correlations:
        print(f"- {col}: {corr}")


if __name__ == '__main__':
    run()