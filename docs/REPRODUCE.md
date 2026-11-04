# Tái lập phần thu trace (NT230)

Từ một VM Ubuntu sạch tới các bảng feature, sensitivity và chi phí. Đọc [SAFETY.md](../SAFETY.md) trước.

Tài liệu chia hai phần. **Phần A** làm theo đúng bài báo DySec. **Phần B** là các thí nghiệm nhóm tự thêm để giải thích vì sao kết quả lệch; số liệu ở phần B không được trình bày như kết quả của DySec.

## 0. Chuẩn bị VM (một lần)

```bash
git clone https://github.com/hoangnxm/ML-Based-Malicious-Package-Detection-NT521.git dysec && cd dysec
cp -r <đường dẫn>/sim_packages ./sim_packages        # bộ gói mô phỏng của Đăng, không commit
sudo bash src/scripts/prerequisites.sh
sudo pip3 install scikit-learn==1.9.0 pandas joblib --break-system-packages   # để chạy demo bằng sudo
chmod +x src/scripts/*.sh

# Khi VM còn mạng:
bash src/scripts/prepare_wheelhouse.sh dataset/our-traces/packages.csv python3   # dependency để cài offline
bash src/scripts/prepare_sdist.sh dataset/our-traces/packages.csv python3        # đóng mọi gói thành .tar.gz
```

`prepare_sdist.sh` ghi ra `dataset/our-traces/packages_sdist.csv` và thư mục `sdist/` (đã có trong `.gitignore`). Sau đó **tạo snapshot** tên `dysec-ready`.

## Phần A. Làm theo bài báo

### A1. Bài báo làm gì, repo làm gì

| Bước | Bài báo DySec | Repo |
|---|---|---|
| Hệ điều hành | Ubuntu 24.04, kernel 6.8 (Raspberry Pi 4) | Ubuntu 24.04, kernel 6.8 (VM x86) |
| Python | 3.8–3.12, mỗi gói một venv mới | 3.12, mỗi gói một venv mới |
| Gói đem cài | chỉ file `.tar.gz` / `.zip` (Algorithm 1, dòng 8) | `packages_sdist.csv`: mọi gói đều là `.tar.gz` |
| Công cụ thu | filetop, opensnoop, tcpstates, strace (theo script tác giả công bố) | giống |
| strace | quét PID python/pip mỗi 1 s | `STRACE=poll`, `POLL=1` (mặc định) |
| Thời gian | 120 s trong và sau khi cài | 120 s |
| pip cache | `--no-cache-dir` | `PIPCACHE=0` (mặc định) |
| Mạng | mạng riêng, cô lập (router và switch riêng) | `NETMODE=fake`: chặn mọi kết nối ra ngoài, chỉ chừa loopback |
| Feature | 36 feature | `src/extract.py`, 36 feature |
| Model | RF, DT, GB, SVM; chia 70/15/15 | `python src/train.py` train đúng 4 model, cùng tham số |
| Lúc dùng thật | chỉ chạy model tốt nhất (RF) | `src/main.py`, `src/predict.py` chỉ chạy RF |

Hai chỗ còn khác và không sửa được: máy (ARM so với x86) và mạng. Quy định NT230 bắt gói mô phỏng phải chạy với mạng tắt hoặc giả lập, nên phần A dùng `NETMODE=fake` cho **cả gói lành lẫn gói mô phỏng**, để hai nhãn chịu cùng một điều kiện mạng.

### A2. Thu trace

```bash
sudo OFFLINE=1 NETMODE=fake DECOYS=1 ./src/scripts/trace_batch.sh dataset/our-traces/packages_sdist.csv paper-d120 120
```

Mất khoảng 50 phút. Kết quả nằm trong `runs/paper-d120/`. Revert snapshot khi xong.

`DECOYS=1` tạo `/root/fake_secret.txt` và biến `FAKE_TOKEN` cho các gói mô phỏng. Script chạy bằng sudo nên `~` là `/root`.

### A3. Xử lý và dự đoán

```bash
python src/collect.py runs/paper-d120        # 4 model của bài báo
python src/manifest.py runs/paper-d120
python src/predict.py runs/paper-d120/features.csv             # kết luận theo RF
python src/predict.py --compare runs/paper-d120/features.csv   # xem thêm DT, GB, SVM
```

### A4. Demo

```bash
sudo OFFLINE=1 NETMODE=fake DECOYS=1 python3 src/main.py sdist/<file sim-exfil-file>.tar.gz 120
cat /tmp/dysec_sim_markers/sim-exfil-file.log     # gói đã làm gì
```

Quay màn hình làm video backup. Revert snapshot sau demo.

## Phần B. Thí nghiệm nhóm tự thêm

Các lượt dưới đây đổi đúng một điều kiện so với phần A, để xem điều kiện đó ảnh hưởng tới feature và kết quả ra sao.

Các lượt đã thu trong `runs/` (d60/d120/d300-fake, delayed, d120-wrap, w2, w3) đều cài gói PyPI từ wheel. Vì vậy chúng thuộc phần B, không phải phần A.

| Thí nghiệm | Khác phần A ở chỗ | Lệnh (thêm `sudo` ở đầu) |
|---|---|---|
| Cài từ wheel | gói PyPI cài từ `.whl`, không build | `OFFLINE=1 NETMODE=fake DECOYS=1 ./src/scripts/trace_batch.sh dataset/our-traces/packages.csv d120-fake 120` |
| Thời lượng 60 s / 300 s | thời gian thu | như trên, tag `d60-fake` / `d300-fake`, số giây `60` / `300` |
| Mạng tắt | không có server giả | `OFFLINE=1 NETMODE=off DECOYS=1 ... packages_sens.csv d120-off 120` |
| strace gắn từ đầu | `STRACE=wrap`, không có trong bài báo | `OFFLINE=1 NETMODE=fake DECOYS=1 STRACE=wrap ... packages.csv d120-wrap 120` |
| Cache pip *(tuỳ chọn)* | `PIPCACHE=1` | chỉ gói benign-pypi, mạng thật: `PIPCACHE=0` một lần, rồi `PIPCACHE=1` hai lần |

Xử lý:

```bash
for r in runs/*/; do python src/collect.py $r --extra; python src/manifest.py $r; done   # --extra: thêm Dummy, LR, KNN

python src/shift.py runs/d120-fake/features.csv --out runs/d120-fake/shift.md
python src/sensitivity.py runs/d120-fake runs/d60-fake runs/d300-fake --out runs/sens_duration.md
python src/sensitivity.py runs/d120-fake runs/d120-off  --out runs/sens_network.md
python src/sensitivity.py runs/d120-fake runs/d120-wrap --out runs/sens_strace.md
```

Dummy, Logistic Regression và KNN không có trong bài báo. Muốn train chúng thì chạy `python src/train.py --extra`; mặc định `train.py` chỉ train 4 model của bài báo.

| File | Dùng cho |
|---|---|
| `runs/<tag>/features.csv` | Hưng: test set cross-dataset (có `Level`, `Group`) |
| `runs/<tag>/errors.csv` | Đăng: error taxonomy FP/FN |
| `runs/<tag>/cost.csv` | bảng chi phí / latency |
| `runs/<tag>/manifest.csv` | data card (SHA256) |
| `runs/*.md` | bảng sensitivity, distribution shift |

## Kiểm tra extractor

Đặt raw và processed QUT-DV25 vào `dataset/QUT-DV25-Raw/` và `dataset/QUT-DV25-Processed/`, rồi chạy `python src/validate.py`. Trên 6 gói mẫu, kết quả là 199/216 giá trị khớp tuyệt đối.
