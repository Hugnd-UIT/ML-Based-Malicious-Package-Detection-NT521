# Tái lập phần thu trace (NT230)

Từ một VM Ubuntu sạch tới các bảng feature, sensitivity và chi phí.

Tài liệu chia hai phần. **Phần A** làm theo đúng bài báo DySec. **Phần B** là các thí nghiệm nhóm tự thêm để giải thích vì sao kết quả lệch; số liệu ở phần B không được trình bày như kết quả của DySec.

## 0. Chuẩn bị VM (một lần)

```bash
git clone https://github.com/hoangnxm/ML-Based-Malicious-Package-Detection-NT230.git dysec && cd dysec
cp -r <đường dẫn>/sim_packages ./sim_packages        # chỉ khi dùng gói mô phỏng; không commit
sudo bash src/scripts/prerequisites.sh
chmod +x src/scripts/*.sh

# Khi VM còn mạng:
bash src/scripts/prepare_wheelhouse.sh data/packages.csv python3   # dependency để cài offline
bash src/scripts/prepare_sdist.sh data/packages.csv python3        # đóng mọi gói thành .tar.gz
```

`prepare_sdist.sh` ghi ra `data/packages_sdist.csv` và thư mục `sdist/` (đã có trong `.gitignore`). Sau đó **tạo snapshot** tên `dysec-ready`.

## Phần A. Làm theo bài báo

### A1. Bài báo làm gì, repo làm gì

| Bước | Bài báo DySec | Repo |
|---|---|---|
| Hệ điều hành | Ubuntu 24.04, kernel 6.8 (Raspberry Pi 4) | Ubuntu 24.04, kernel 6.8 (VM x86) |
| Python | 3.12 cho gói lành, 3.8 cho gói độc (suy ra từ trace thô QUT-DV25), mỗi gói một venv mới | `PYTHON=python3` (3.12); `PYTHON=python3.8` cho gói độc |
| pip / setuptools / wheel | 24.3.1 / 75.3.0 / 0.43.0 (lành), 0.45.1 (độc), theo trace thô QUT-DV25 | `trace.sh` ghim đúng các bản này |
| Lệnh cài | `pip install <gói> --break-system-packages --no-build-isolation --no-cache-dir`, lỗi thì thử lại 2 lần (script tác giả) | giống |
| Gói đem cài | chỉ file `.tar.gz` / `.zip` (Algorithm 1, dòng 8) | `packages_sdist.csv`: mọi gói đều là `.tar.gz` |
| Công cụ thu | filetop, opensnoop, tcpstates, strace (theo script tác giả công bố); chờ 5 s trước khi cài | giống |
| strace | quét PID python/pip mỗi 1 s | `STRACE=poll`, `POLL=1` (mặc định) |
| Thời gian | 120 s trong và sau khi cài | 120 s |
| pip cache | `--no-cache-dir` | `PIPCACHE=0` (mặc định) |
| Mạng | mạng riêng, cô lập; pip tải dependency từ PyPI | `NETMODE=mirror`: chặn mọi kết nối ra ngoài; pip tải gói và dependency qua mạng từ chỉ mục giả trên 127.0.0.1:8081 (đề R49 bắt mạng tắt hoặc giả lập) |
| Feature | 36 feature | `src/extract.py`, 36 feature |
| Model | RF, DT, GB, SVM; chia 70/15/15 | `python src/train.py` train đúng 4 model, cùng tham số |
| Lúc dùng thật | chỉ chạy model tốt nhất (RF) | `src/main.py`, `src/predict.py` chỉ chạy RF |

Chỗ còn khác và không sửa được: máy (ARM so với x86). Bản `trace.sh` trước 13/11/2026 chưa có cờ `--no-build-isolation` và chưa ghim pip, nên mọi lượt trong `results/runs/` thu trước ngày đó **không** thuộc phần A (xem [results/README.md](../results/README.md)). Khác thêm: pip tải từ chỉ mục giả trên loopback chứ không từ PyPI thật, nên không có truy vấn DNS và kết nối ra Internet trong trace.

### A2. Thu trace

```bash
sudo NETMODE=mirror DECOYS=1 ./src/scripts/trace_batch.sh data/packages_sdist.csv paper-mirror-d120 120
```

Mất khoảng 50 phút. Kết quả nằm trong `results/runs/paper-mirror-d120/`. Revert snapshot khi xong.

`DECOYS=1` tạo `/root/fake_secret.txt` và biến `FAKE_TOKEN` cho các gói mô phỏng. Script chạy bằng sudo nên `~` là `/root`.

### A3. Xử lý và dự đoán

```bash
python src/collect.py results/runs/paper-mirror-d120        # 4 model của bài báo
python src/manifest.py results/runs/paper-mirror-d120
python src/predict.py results/runs/paper-mirror-d120/features.csv             # kết luận theo RF
python src/predict.py --compare results/runs/paper-mirror-d120/features.csv   # xem thêm DT, GB, SVM
```

### A4. Demo

```bash
sudo NETMODE=mirror DECOYS=1 python3 src/main.py sdist/<file sim-exfil-file>.tar.gz 120
cat /tmp/dysec_sim_markers/sim-exfil-file.log     # gói đã làm gì
```

Quay màn hình làm video backup. Revert snapshot sau demo.

## Phần B. Thí nghiệm nhóm tự thêm

Các lượt dưới đây đổi đúng một điều kiện so với phần A, để xem điều kiện đó ảnh hưởng tới feature và kết quả ra sao.

Các lượt đã thu trong `results/runs/` (d60/d120/d300-fake, delayed, d120-wrap, w2, w3) đều cài gói PyPI từ wheel, nên thuộc phần B. `paper-d120` cài từ `.tar.gz` nhưng dependency lấy offline từ wheelhouse (`NETMODE=fake`), nên cũng thuộc phần B.

| Thí nghiệm | Khác phần A ở chỗ | Lệnh (thêm `sudo` ở đầu) |
|---|---|---|
| Cài từ wheel | gói PyPI cài từ `.whl`, không build | `OFFLINE=1 NETMODE=fake DECOYS=1 ./src/scripts/trace_batch.sh data/packages.csv d120-fake 120` |
| Thời lượng 60 s / 300 s | thời gian thu | như trên, tag `d60-fake` / `d300-fake`, số giây `60` / `300` |
| Mạng tắt | không có server giả | `OFFLINE=1 NETMODE=off DECOYS=1 ... packages_sens.csv d120-off 120` |
| strace gắn từ đầu | `STRACE=wrap`, không có trong bài báo | `OFFLINE=1 NETMODE=fake DECOYS=1 STRACE=wrap ... packages.csv d120-wrap 120` |
| Cache pip *(tuỳ chọn)* | `PIPCACHE=1` | chỉ gói benign-pypi, mạng thật: `PIPCACHE=0` một lần, rồi `PIPCACHE=1` hai lần |

Xử lý:

```bash
for r in results/runs/*/; do python src/collect.py $r --extra; python src/manifest.py $r; done   # --extra: thêm Dummy, LR, KNN

python src/shift.py results/runs/d120-fake/features.csv --out results/runs/d120-fake/shift.md
python src/sensitivity.py results/runs/d120-fake results/runs/d60-fake results/runs/d300-fake --out results/runs/sens_duration.md
python src/sensitivity.py results/runs/d120-fake results/runs/d120-off  --out results/runs/sens_network.md
python src/sensitivity.py results/runs/d120-fake results/runs/d120-wrap --out results/runs/sens_strace.md
```

Dummy, Logistic Regression và KNN không có trong bài báo. Muốn train chúng thì chạy `python src/train.py --extra`; mặc định `train.py` chỉ train 4 model của bài báo.

| File | Dùng cho |
|---|---|
| `results/runs/<tag>/features.csv` | Hưng: test set cross-dataset (có `Level`, `Group`) |
| `results/runs/<tag>/errors.csv` | Đăng: error taxonomy FP/FN |
| `results/runs/<tag>/cost.csv` | bảng chi phí / latency |
| `results/runs/<tag>/manifest.csv` | data card (SHA256) |
| `results/runs/*.md` | bảng sensitivity, distribution shift |

## Kiểm tra extractor

Đặt raw và processed QUT-DV25 vào `dataset/QUT-DV25-Raw/` và `dataset/QUT-DV25-Processed/`, rồi chạy `python src/validate.py`. Trên 6 gói mẫu, kết quả là 199/216 giá trị khớp tuyệt đối.
