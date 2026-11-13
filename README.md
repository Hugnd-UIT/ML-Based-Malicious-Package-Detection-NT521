# DySec — NT230 đề R49

Tái lập DySec (phát hiện gói PyPI độc hại bằng phân tích động lúc `pip install`, eBPF + strace + Random Forest) và đo xem kết quả thay đổi thế nào khi đổi môi trường thu trace.

- Bài báo: S. T. Mehedi, C. Islam, G. Ramachandran, R. Jurdak, *DySec: A Machine Learning-Based Dynamic Analysis for Detecting Malicious Packages in PyPI Ecosystem*, IEEE TIFS 21, 2026, [doi:10.1109/TIFS.2026.3654388](https://doi.org/10.1109/TIFS.2026.3654388) ([PDF](docs/papers/DySec-A-Machine-Learning-Based-Dynamic-Analysis-For-Detecting-Malicious-Packages-In-PyPI-Ecosystem.pdf)).
- Dataset gốc: QUT-DV25, 14.271 gói (7.127 độc, 7.144 lành), xem [dataset/README.md](dataset/README.md).
- Nhóm: Ngô Xuân Minh Hoàng, Nguyễn Duy Hưng, Nguyễn Hoàng Khánh Đăng.

## Thư mục

```
src/                 code
  scripts/           thu trace trong VM: trace.sh, monitor.sh, prepare_mirror.sh, prerequisites.sh
  harness/           server giả trên 127.0.0.1 (C2, HTTP) và file mồi, dùng khi NETMODE=fake/mirror
  extract.py         raw trace -> 36 feature
  preprocess.py, train.py, evaluate.py, predict.py, main.py   pipeline model (4 model của bài báo, RF để kết luận)
  authors.py         pipeline n-gram theo notebook của tác giả
  batch.py           chạy danh sách gói: trace -> feature -> điểm, ghi latency và dung lượng trace
  ablation.py        ablation theo 7 nhóm feature
  variant/           model bỏ G1+G2 / G1+G2+G3; script lần A–E (NT521) và F1–F6 (NT230); compare_runs.py
  data/              chọn dữ liệu, chia train/val/test, EDA, tạo danh sách lượt đo
data/                danh sách gói (benign-*.txt, malicious-*.txt, mix-lapE.txt 270 gói, mix-sens.txt 100 gói)
dataset/             QUT-DV25 đã xử lý (train/val/test)
models/              model đã train (models/variant/, models/authors/ sinh lại bằng script)
results/             số liệu: qut-test/, ablation/, nt230/<lượt>/  (xem results/README.md)
reports/             báo cáo Word; reports/doi-tuong/ là phần hiểu đối tượng mã độc
docs/                REPRODUCE.md, protocols/, 36-features.md, authors-code.md, DEMO.md, papers/
```

## Đối chiếu với yêu cầu đề R49

Nhóm **không** làm dataset mới (mục tùy chọn), nên rubric 3 tính theo nhánh "phân tích sâu dataset gốc". Trạng thái ghi theo ngày 13/11/2026.

| Yêu cầu (YC_R49 / rubric) | Minh chứng | Trạng thái |
|---|---|---|
| **1. Hiểu đối tượng**: concept map, threat model, định nghĩa nhãn, bảng đặc trưng | `reports/doi-tuong/`, `docs/36-features.md` | có, cần đối chiếu lại với rubric 1 |
| **2. Tái lập**: pipeline dữ liệu → feature → model, baseline, protocol, metric; bảng so với bài gốc | `src/`, `results/qut-test/`, `docs/REPRODUCE.md` mục 5, `docs/authors-code.md`, `docs/README_goc_NT521.md` | có; thiếu bảng 3 cột tái lập được / cải tiến / không tái lập |
| Baseline ML tầm thường | `python src/evaluate.py --extra` (Dummy, LR, KNN) | có |
| **Baseline metadata/static** | `baseline_static.py` | **chưa có** |
| Ablation, seed, phiên bản | `results/ablation/`, `src/variant/`, `requirements.txt`, 6 seed trong `evaluate.py` | có |
| **Harness mạng tắt / giả lập**, quy trình thu, schema feature | `src/scripts/trace.sh` (`NETMODE=off` / `fake` / `mirror`), `src/harness/`, `docs/REPRODUCE.md`, `docs/36-features.md`, `src/validate.py` (khớp 199/216 giá trị với CSV tác giả) | có; `mirror` chưa chạy trong VM |
| **3. Phân tích sâu dataset gốc**: bias, leakage, giới hạn, trùng lặp, mất cân bằng, cross-family split | `src/data/eda.py`, `src/data/split-data.py` (chia theo họ tên gói), `docs/authors-code.md` (rò rỉ thứ tự `Unique_*_List`) | một phần; chưa viết thành mục (Python 3.8/3.12 và `.tar.gz` gắn với nhãn, gói đổi tên…) |
| **4. Thực nghiệm**: P/R/F1/FPR, confusion matrix, FN, error taxonomy, CI | `results/qut-test/`; lần C/D (Wilson CI, McNemar); F1–F6 | lần C/D có; F1–F6 chưa chạy; error taxonomy chưa có |
| Latency sau trích feature, chi phí thu | cột `Extract_Seconds`, `Predict_Seconds`, `Install_Seconds`, `Trace_Bytes` trong `*_results.csv` | sẽ có sau F1 |
| **Tác động của OS, thời gian chạy, dependency, sandbox** | F2 (mạng tắt), F3/F4 (60/300 s), F5 (`--no-deps`), F6 (Ubuntu 22.04) so cặp với F1, luật ở `docs/protocols/PROTOCOL-NT230.md` | chưa chạy |
| Phân tầng (typosquat, install hook, file/network, kiểu hành vi); hành vi chưa kích hoạt / trì hoãn | F1 + `baseline_static.py` (vị trí payload: `setup.py` hay `__init__.py`) | chưa có |
| Threats to validity | báo cáo | chưa có |
| **5. Tái lập, đạo đức**: README, environment, checksum, snapshot/rollback, demo | README, `requirements.txt`, sha256 model và file kết quả in trong log mỗi lượt, `docs/REPRODUCE.md`, `docs/DEMO.md` | có; thiếu video demo |

## Chạy

- Máy thật (không cần VM): `pip install -r requirements.txt`, rồi `python src/evaluate.py`, `python src/ablation.py`. Xem [docs/REPRODUCE.md](docs/REPRODUCE.md) mục 4.
- Trong VM: các lượt F1–F6 theo [docs/REPRODUCE.md](docs/REPRODUCE.md) mục 0–3.

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
