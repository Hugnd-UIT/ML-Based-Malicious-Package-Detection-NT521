# DySec — NT230 đề R49

Tái lập DySec (phát hiện gói PyPI độc hại bằng phân tích động lúc `pip install`, eBPF + strace + Random Forest) và đo xem kết quả thay đổi thế nào khi đổi môi trường thu trace.

- Bài báo: S. T. Mehedi, C. Islam, G. Ramachandran, R. Jurdak, *DySec: A Machine Learning-Based Dynamic Analysis for Detecting Malicious Packages in PyPI Ecosystem*, IEEE TIFS 21, 2026, [doi:10.1109/TIFS.2026.3654388](https://doi.org/10.1109/TIFS.2026.3654388) ([PDF](docs/papers/DySec-A-Machine-Learning-Based-Dynamic-Analysis-For-Detecting-Malicious-Packages-In-PyPI-Ecosystem.pdf)).
- Dataset gốc: QUT-DV25, 14.271 gói (7.127 độc, 7.144 lành), xem [dataset/README.md](dataset/README.md).
- Nhóm: Ngô Xuân Minh Hoàng, Nguyễn Duy Hưng, Nguyễn Hoàng Khánh Đăng.

## Thư mục

```
src/                 code
  scripts/           thu trace trong VM: trace.sh, monitor.sh, trace_batch.sh, rerun_failed.sh, prepare_*.sh
  extract.py         raw trace -> 36 feature
  preprocess.py, train.py, evaluate.py, predict.py, main.py   pipeline model (4 model của bài báo)
  authors.py         pipeline n-gram theo notebook của tác giả
  batch.py           chạy danh sách gói, chấm điểm ngay lúc đo
  collect.py, manifest.py, shift.py, sensitivity.py           xử lý một lượt thu (results/runs/<tag>)
  ablation.py        ablation theo 7 nhóm feature
  variant/           model bỏ G1+G2 / G1+G2+G3, script chạy lần A–E
  data/              chọn dữ liệu, chia train/val/test, EDA
data/                danh sách gói đem thu (packages*.csv, benign-*.txt, malicious-*.txt)
dataset/             QUT-DV25 đã xử lý (train/val/test) + our-traces/DATACARD.md
models/              model đã train (models/variant/, models/authors/ sinh lại bằng script)
results/             số liệu: qut-test/, ablation/, runs/<tag>/  (xem results/README.md)
reports/             báo cáo Word; reports/doi-tuong/ là phần hiểu đối tượng mã độc (Đăng)
docs/                REPRODUCE.md, DEMO.md, 36-features.md, authors-code.md, protocols/, papers/
```

## Đối chiếu với yêu cầu đề R49

Cột "Trạng thái" ghi đúng hiện trạng ngày 13/11/2026.

| Yêu cầu (YC_R49 / rubric) | Minh chứng | Trạng thái |
|---|---|---|
| **1. Hiểu đối tượng**: concept map, threat model, định nghĩa nhãn, bảng đặc trưng | `reports/doi-tuong/` (TTP_ConceptMap, ThreatModel, DinhNghiaNhan_DacTrung, CauHoiNghienCuu), `docs/36-features.md` | có, cần đối chiếu lại với rubric 1 |
| **2. Tái lập**: pipeline dữ liệu → feature → model, baseline, protocol, metric | `src/`, `results/qut-test/`, `docs/authors-code.md` (so với code tác giả), `docs/README_goc_NT521.md` (so với bài báo) | có |
| Baseline ML tầm thường | `python src/evaluate.py --extra` (thêm Dummy, LR, KNN) | có |
| **Baseline metadata/static** (đề yêu cầu đối chiếu) | `baseline_static.py` | **chưa có** |
| Ablation / seed / phiên bản | `results/ablation/`, `src/variant/`, `requirements.txt` (ghim phiên bản), 6 seed trong `evaluate.py` | có |
| **Harness mạng tắt / giả lập** | `src/scripts/trace.sh` `NETMODE=off` / `fake` / `mirror`, server giả ở `src/harness/` | có; các lượt cũ trong `results/runs/` dùng `fake` hoặc `pypi` (pypi là mạng thật tới PyPI, không tính là giả lập) |
| Quy trình thu trace, schema feature | `docs/REPRODUCE.md`, `docs/36-features.md`, `src/extract.py`, `src/validate.py` (khớp 199/216 giá trị với CSV tác giả) | có |
| **3. Dataset** (tùy chọn): nếu đóng góp thì nguồn, nhãn, schema, license, chia tập, data card; nếu không thì phân tích sâu dataset gốc | `dataset/our-traces/DATACARD.md`, `data/packages*.csv`, `results/runs/<tag>/manifest.csv` | bản nháp; thiếu license từng gói, chưa chia tập |
| Phân tích dataset gốc: bias, trùng lặp, leakage | `src/data/eda.py`, `docs/authors-code.md` (rò rỉ thứ tự `Unique_*_List`) | một phần |
| **4. Thực nghiệm**: P/R/F1/FPR, confusion matrix, FN, error taxonomy | `results/qut-test/`, `results/runs/<tag>/errors.csv` | có; error taxonomy chưa xong |
| CI / seed, cross-dataset | lần A–E (Wilson CI, McNemar) ở `src/variant/`, `results/runs/` | có |
| Latency sau trích feature, chi phí thu | `results/runs/<tag>/cost.csv` | có |
| **Tác động của OS, thời gian chạy, dependency, sandbox** | thời gian: `d60/d120/d300`; sandbox: `NETMODE`; dependency: wheel / `.tar.gz` / online; OS: — | **thiếu OS và `--no-deps`**; phải thu lại bằng `trace.sh` mới |
| Hành vi trì hoãn / chưa kích hoạt lúc cài | `delayed-120`, `delayed-300`, sim-import-only | có (thu bằng script cũ) |
| Threats to validity | báo cáo | chưa xong |
| **5. Tái lập, đạo đức**: README, environment, checksum, snapshot/rollback, demo | README, `requirements.txt`, `manifest.csv`, `docs/DEMO.md` | có; thiếu video demo |

## Chạy nhanh

Trên máy thật (không cần VM):

```bash
pip install -r requirements.txt
python src/evaluate.py                       # 4 model trên test QUT-DV25 -> results/qut-test/
python src/ablation.py                       # ablation -> results/ablation/
python src/variant/train_variant.py          # model bỏ G1+G2 -> models/variant/
python src/predict.py results/runs/paper-pypi-d120/features.csv   # chấm lại một lượt đã thu
```

Thu trace thì chỉ chạy trong VM có snapshot, theo [docs/REPRODUCE.md](docs/REPRODUCE.md).

## Trích dẫn

```bibtex
@article{Mehedi2025DySec,
  author  = {Sk Tanzir Mehedi and Chadni Islam and Gowri Ramachandran and Raja Jurdak},
  title   = {DySec: A Machine Learning-based Dynamic Analysis for Detecting Malicious Packages in the PyPI Ecosystem},
  journal = {arXiv preprint arXiv:2503.00324},
  year    = {2025}
}
```

Giấy phép: [LICENSE.md](LICENSE.md).
