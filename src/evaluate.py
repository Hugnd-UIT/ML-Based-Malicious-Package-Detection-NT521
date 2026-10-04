import gc
import os
import time
import joblib
import collections

import numpy as np
import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report
)

try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    PLT_AVAILABLE = True
except ImportError:
    PLT_AVAILABLE = False


BASE_DIR = (
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if '__file__' in globals()
    else os.path.abspath('.')
)

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from preprocess import transform
from train import get_models, load_partition

DATA_PATH = os.path.join(
    BASE_DIR,
    'dataset',
    'test.csv'
)

TRAIN_PATH = os.path.join(
    BASE_DIR,
    'dataset',
    'train.csv'
)

MODELS_DIR = os.path.join(
    BASE_DIR,
    'models'
)

REPORTS_DIR = os.path.join(
    BASE_DIR,
    'reports'
)
os.makedirs(REPORTS_DIR, exist_ok=True)

MODEL_NAMES = [
    'Dummy-Classifier',
    'Random-Forest',
    'Decision-Tree',
    'Gradient-Boosting',
    'SVM',
    'Logistic-Regression',
    'KNN'
]


def load_test_data(path):
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"[!] Test dataset not found: {path}"
        )

    print(
        f"[*] Reading: {os.path.basename(path)}"
    )

    t = time.time()
    df = pd.read_csv(path)

    y = df.pop('Level').values

    if 'Package_Name' in df.columns:
        df.drop(
            columns=['Package_Name'],
            inplace=True
        )

    X = transform(df)

    print(
        f"\n[+] Loaded: {len(X):,} test samples | {X.shape[1]} features"
    )
    print(
        f"[+] Completed in {time.time() - t:.2f}s"
    )

    return X, y


def evaluate_model(name, model, X, y):
    print("\n" + "=" * 60)
    print(
        f"[*] Evaluating: {name}"
    )
    print("=" * 60)

    t_start = time.time()

    preds = model.predict(X)

    try:
        probs = model.predict_proba(X)[:, 1]
        auc = roc_auc_score(y, probs)
    except Exception:
        probs = None
        auc = 0.0

    duration = time.time() - t_start

    acc = accuracy_score(y, preds)
    prec = precision_score(y, preds, zero_division=0)
    rec = recall_score(y, preds, zero_division=0)
    f1 = f1_score(y, preds, zero_division=0)

    cm = confusion_matrix(y, preds)
    tn, fp, fn, tp = cm.ravel()
    total = len(y)

    fpr = (fp / (fp + tn)) if (fp + tn) > 0 else 0.0
    fnr = (fn / (fn + tp)) if (fn + tp) > 0 else 0.0

    print(
        f"[+] Finished in {duration:.2f}s"
    )
    print(
        f"    Accuracy : {acc * 100:.2f}%"
    )
    print(
        f"    Precision: {prec * 100:.2f}%"
    )
    print(
        f"    Recall   : {rec * 100:.2f}%"
    )
    print(
        f"    F1-Score : {f1 * 100:.2f}%"
    )
    print(
        f"    ROC-AUC  : {auc:.4f}"
    )

    print("\n[*] Confusion Matrix:")
    print(
        f"    TN (Benign -> Benign)      : {tn:>6,} ({tn / total * 100:>5.2f}%)"
    )
    print(
        f"    FP (Benign -> Malicious)   : {fp:>6,} ({fp / total * 100:>5.2f}%)"
    )
    print(
        f"    FN (Malicious -> Benign)   : {fn:>6,} ({fn / total * 100:>5.2f}%)"
    )
    print(
        f"    TP (Malicious -> Malicious): {tp:>6,} ({tp / total * 100:>5.2f}%)"
    )

    print("\n[*] Classification Report:")
    print(
        classification_report(
            y,
            preds,
            target_names=['Benign', 'Malicious'],
            digits=4,
            zero_division=0
        )
    )

    return {
        'Model': name,
        'Accuracy': round(acc, 4),
        'Precision': round(prec, 4),
        'Recall': round(rec, 4),
        'F1_Score': round(f1, 4),
        'ROC_AUC': round(auc, 4),
        'TP': int(tp),
        'TN': int(tn),
        'FP': int(fp),
        'FN': int(fn),
        'FPR': round(fpr, 4),
        'FNR': round(fnr, 4),
        'probs': probs,
        'cm': cm
    }


def plot_confusion_matrices(results, save_path):
    if not PLT_AVAILABLE or not results:
        return

    n = len(results)
    cols = 3 if n > 4 else 2
    rows = int(np.ceil(n / cols))

    fig, axes = plt.subplots(
        rows,
        cols,
        figsize=(6 * cols, 5 * rows)
    )
    axes = np.array(axes).flatten()

    for idx, res in enumerate(results):
        cm = res['cm']
        total = np.sum(cm)
        percentages = cm / total * 100

        labels = [
            f"{val:,}\n({pct:.1f}%)"
            for val, pct in zip(cm.flatten(), percentages.flatten())
        ]
        labels = np.asarray(labels).reshape(2, 2)

        sns.heatmap(
            cm,
            annot=labels,
            fmt='',
            cmap='Blues',
            ax=axes[idx],
            cbar=False,
            xticklabels=['Benign', 'Malicious'],
            yticklabels=['Benign', 'Malicious']
        )

        axes[idx].set_title(
            f"{res['Model']} (Acc: {res['Accuracy'] * 100:.2f}%)",
            fontsize=12,
            fontweight='bold'
        )
        axes[idx].set_xlabel('Predicted Label')
        axes[idx].set_ylabel('True Label')

    for idx in range(n, len(axes)):
        fig.delaxes(axes[idx])

    plt.tight_layout()
    plt.savefig(
        save_path,
        dpi=300
    )
    plt.close()

    print(
        f"[+] Confusion matrices saved to: {save_path}"
    )


def plot_roc_curves(results, y_test, save_path):
    if not PLT_AVAILABLE:
        return

    from sklearn.metrics import roc_curve

    plt.figure(
        figsize=(8, 6)
    )

    for res in results:
        if res['probs'] is not None:
            fpr, tpr, _ = roc_curve(
                y_test,
                res['probs']
            )
            plt.plot(
                fpr,
                tpr,
                label=f"{res['Model']} (AUC = {res['ROC_AUC']:.4f})",
                linewidth=2
            )

    plt.plot(
        [0, 1],
        [0, 1],
        'k--',
        label='Random Guess',
        alpha=0.6
    )

    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate (FPR)', fontsize=11)
    plt.ylabel('True Positive Rate (TPR)', fontsize=11)
    plt.title('ROC Curves - PyPI Malicious Package Detection', fontsize=13, fontweight='bold')
    plt.legend(loc='lower right', fontsize=10)
    plt.grid(True, linestyle='--', alpha=0.5)

    plt.tight_layout()
    plt.savefig(
        save_path,
        dpi=300
    )
    plt.close()

    print(
        f"[+] ROC curves saved to: {save_path}"
    )


def plot_table(csv_path, save_path):
    if not PLT_AVAILABLE:
        return
    data = pd.read_csv(csv_path)
    fig, ax = plt.subplots(figsize=(14, 3.5))
    ax.axis('off')
    ax.axis('tight')

    table = ax.table(
        cellText=data.values,
        colLabels=data.columns,
        loc='center',
        cellLoc='center'
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.8)

    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor('#1f4e79')
            cell.set_text_props(color='white', weight='bold')
        elif row % 2 == 0:
            cell.set_facecolor('#f2f4f8')
        else:
            cell.set_facecolor('#ffffff')
        cell.set_edgecolor('#d0d5dd')

    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()


def main():
    total_start = time.time()

    X_test, y_test = load_test_data(DATA_PATH)
    X_train, y_train = load_partition(TRAIN_PATH, 'Train')

    seeds = [50, 100, 150, 500, 1000, 5000]
    records = collections.defaultdict(lambda: collections.defaultdict(list))
    base_results = []

    for seed in seeds:
        print("\n" + "=" * 60)
        print(f"[*] Running seed: {seed}")
        print("=" * 60)

        models = get_models(seed)

        for name, model in models.items():
            model.fit(X_train, y_train)

            if seed == 50:
                save_name = name.replace(' ', '-') + '.pkl'
                joblib.dump(model, os.path.join(MODELS_DIR, save_name))

            res = evaluate_model(name, model, X_test, y_test)

            if seed == 50:
                base_results.append(res)

            for key in ('Accuracy', 'Precision', 'Recall', 'F1_Score', 'ROC_AUC', 'FPR', 'FNR'):
                records[name][key].append(res[key])

            del model
            gc.collect()

    summary_rows = []
    metric_cols = ('Accuracy', 'Precision', 'Recall', 'F1_Score', 'ROC_AUC', 'FPR', 'FNR')

    for name in models.keys():
        row = {'Model': name}
        for key in metric_cols:
            vals = records[name][key]
            val_mean = np.mean(vals)
            val_std = np.std(vals)
            row[key] = f"{val_mean:.4f} ± {val_std:.4f}"
        summary_rows.append(row)

    summary_df = pd.DataFrame(summary_rows)
    display_cols = ['Model'] + list(metric_cols)

    print("\n" + "=" * 60)
    print("[*] Summary:")
    print("=" * 60)
    print(summary_df[display_cols].to_string(index=False))

    csv_path = os.path.join(REPORTS_DIR, 'model-performance.csv')
    summary_df[display_cols].to_csv(csv_path, index=False)
    print(f"\n[+] Saved evaluation summary: {csv_path}")

    img_path = os.path.join(REPORTS_DIR, 'model-performance.png')
    plot_table(csv_path, img_path)
    print(f"[+] Saved evaluation table image: {img_path}")

    cm_path = os.path.join(REPORTS_DIR, 'confusion-matrices.png')
    roc_path = os.path.join(REPORTS_DIR, 'roc-curves.png')

    plot_confusion_matrices(base_results, cm_path)
    plot_roc_curves(base_results, y_test, roc_path)

    del X_train, y_train, X_test, y_test, records, summary_df
    gc.collect()


if __name__ == '__main__':
    main()
