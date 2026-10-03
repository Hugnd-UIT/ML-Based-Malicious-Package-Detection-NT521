# A Machine Learning-Based Dynamic Analysis for Detecting Malicious Packages in PyPI Ecosystem

A Linux kernel-level dynamic behavioral analysis system utilizing eBPF and `strace` combined with Machine Learning classifiers to detect supply chain attacks and malicious packages in the PyPI ecosystem, replicating and extending the DySec framework (QUT-DV25).

---

## Directory Structure

```
.
├── dataset/
│   ├── QUT-DV25.csv
│   ├── README.md
│   ├── test.csv
│   ├── train.csv
│   └── val.csv
├── models/
│   ├── Decision-Tree.pkl
│   ├── Gradient-Boosting.pkl
│   ├── KNN.pkl
│   ├── Logistic-Regression.pkl
│   ├── Random-Forest.pkl
│   └── SVM.pkl
├── reports/
│   ├── confusion.png
│   ├── evaluation.csv
│   └── roc.png
├── src/
│   ├── scripts/
│   │   ├── monitor.sh
│   │   ├── prerequisites.sh
│   │   └── trace.sh
│   ├── evaluate.py
│   ├── extract.py
│   ├── main.py
│   ├── predict.py
│   ├── preprocess.py
│   └── train.py
├── .gitignore
└── README.md
```

---

## Installation & Setup

Open a terminal in the root directory of the repository and execute:

```bash
sudo bash src/scripts/prerequisites.sh
chmod +x src/scripts/trace.sh src/scripts/monitor.sh
```

---

## Usage Guide

### 1. Automated End-to-End Pipeline

Run the full pipeline (live dynamic tracing $\rightarrow$ 36-feature extraction to CSV $\rightarrow$ multi-model AI consensus prediction) using a single command:

```bash
sudo python3 src/main.py <package_name> [duration]
```

*Example:*
```bash
sudo python3 src/main.py requests 30
```

*If traces already exist and you want to extract and predict without re-installing:*
```bash
python3 src/main.py requests --skip
```

---

### 2. Manual Step-by-Step Execution

#### Step 1: Capture Dynamic Telemetry
Attach eBPF probes (`opensnoop`, `tcpstates`, `filetop`) and `strace` during isolated package installation:

```bash
sudo bash src/scripts/trace.sh requests 30
```

#### Step 2: Extract 36 Selected Engineered Features (SEF)
Parse raw kernel logs into an empirical 36-feature CSV evidence file:

```bash
python3 src/extract.py --pkg requests --out requests.csv
```

#### Step 3: Run Multi-Model AI Prediction
Feed the extracted CSV evidence into the trained classifiers:

```bash
python3 src/predict.py requests.csv
```

---

## Training & Evaluation

### Train Models:
Train all 6 classifiers on the partitioned training dataset (`dataset/train.csv`):

```bash
python3 src/train.py
```

### Evaluate on Test Set:
Benchmark the models on the independent test dataset (`dataset/test.csv`) and generate evaluation reports:

```bash
python3 src/evaluate.py
```

---

## Experimental Benchmark

### Comprehensive Evaluation on Test Set (2,141 Samples)

| # | Model | Accuracy | Precision | Recall | F1-Score | ROC-AUC | FPR | FNR |
| :-: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | **Gradient Boosting** | **98.23%** | **98.22%** | **98.22%** | **98.22%** | **0.9986** | **1.77%** | **1.78%** |
| 2 | **Random Forest** | **96.36%** | **96.79%** | **95.88%** | **96.33%** | **0.9951** | **3.17%** | **4.12%** |
| 3 | **Decision Tree** | **95.00%** | **95.64%** | **94.29%** | **94.96%** | **0.9784** | **4.29%** | **5.71%** |
| 4 | **SVM (LinearSVC)** | **89.30%** | **90.86%** | **87.37%** | **89.08%** | **0.9557** | **8.77%** | **12.63%** |
| 5 | **Logistic Regression** *(Extension)* | **86.74%** | **88.90%** | **83.91%** | **86.33%** | **0.9387** | **10.45%** | **16.09%** |
| 6 | **KNN (k=5)** *(Extension)* | **81.27%** | **82.49%** | **79.33%** | **80.88%** | **0.8891** | **16.79%** | **20.67%** |

*Generated artifacts in `reports/`:*
- Confusion Matrices: `reports/confusion.png`
- ROC Curves: `reports/roc.png`
- Metrics Summary: `reports/evaluation.csv`

---

### Comparison with DySec Published Results

| Classifier | Published Accuracy (DySec) | Replicated Accuracy (Ours) | Delta ($\Delta$) | Status |
| :--- | :---: | :---: | :---: | :--- |
| **Random Forest** | ~95.99% | **96.36%** | **+0.37%** | Consistent match with paper findings |
| **Gradient Boosting** | ~96.50% - 97.20% | **98.23%** | **+1.03%** | Superior generalization performance |
| **Decision Tree** | ~93.80% - 94.50% | **95.00%** | **+0.50%** | Matches tree-based baseline |
| **SVM** | ~88.00% - 90.00% | **89.30%** | **-0.20%** | Consistent with linear boundary baselines |
