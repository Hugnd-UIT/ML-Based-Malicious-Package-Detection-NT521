# Tái lập phần thu trace (NT230)

Từ một VM Ubuntu sạch tới các bảng feature, sensitivity và chi phí. Đọc [SAFETY.md](../SAFETY.md) trước.

## 0. Chuẩn bị VM (một lần)

```bash
git clone https://github.com/hoangnxm/ML-Based-Malicious-Package-Detection-NT521.git dysec && cd dysec
cp -r <đường dẫn>/sim_packages ./sim_packages        # bộ gói mô phỏng của Đăng, không commit
sudo bash src/scripts/prerequisites.sh
sudo pip3 install scikit-learn==1.9.0 pandas joblib --break-system-packages   # để chạy demo bằng sudo
chmod +x src/scripts/*.sh

# Khi VM còn mạng: tải sẵn wheel cho chế độ offline
bash src/scripts/prepare_wheelhouse.sh dataset/our-traces/packages.csv python3
```

Sau đó **tạo snapshot** tên `dysec-ready`.

## 1. Thu bộ dữ liệu chính (21 gói, 120 s, mạng giả lập)

```bash
sudo OFFLINE=1 NETMODE=fake DECOYS=1 ./src/scripts/trace_batch.sh dataset/our-traces/packages.csv d120-fake 120
```

Mất khoảng 21 × 2.3 phút ≈ 50 phút. Kết quả nằm trong `runs/d120-fake/`. Revert snapshot khi xong.

`DECOYS=1` tạo `/root/fake_secret.txt` và biến `FAKE_TOKEN` cho các gói mô phỏng. Script chạy bằng sudo nên `~` là `/root`.

## 2. Thí nghiệm sensitivity (8 gói của `packages_sens.csv`)

| Thí nghiệm | Lệnh (thêm `sudo` ở đầu) | Run tag |
|---|---|---|
| (a) thời lượng 60 s | `OFFLINE=1 NETMODE=fake DECOYS=1 ./src/scripts/trace_batch.sh dataset/our-traces/packages_sens.csv d60-fake 60` | `d60-fake` |
| (a) thời lượng 300 s | như trên, tag `d300-fake`, `300` | `d300-fake` |
| (b) mạng tắt | `OFFLINE=1 NETMODE=off DECOYS=1 ... packages_sens.csv d120-off 120` | `d120-off` |
| (e) strace gắn từ đầu | `OFFLINE=1 NETMODE=fake DECOYS=1 STRACE=wrap ... packages.csv d120-wrap 120` | `d120-wrap` |
| (c) cache pip *(tuỳ chọn)* | chỉ gói benign-pypi, mạng thật: chạy `PIPCACHE=0` một lần, rồi `PIPCACHE=1` hai lần, so lần 1 với lần 3 | `cache0`, `cache1`, `cache2` |

Mốc 120 s của (a) lấy luôn từ `d120-fake` ở bước 1. Nếu thiếu thời gian thì chỉ làm (a).

## 3. Xử lý (chạy được trên máy thật, không cần sudo)

Copy thư mục `runs/` ra máy thật rồi chạy:

```bash
for r in runs/*/; do python src/collect.py $r; python src/manifest.py $r; done

python src/shift.py runs/d120-fake/features.csv --out runs/d120-fake/shift.md
python src/sensitivity.py runs/d120-fake runs/d60-fake runs/d300-fake --out runs/sens_duration.md
python src/sensitivity.py runs/d120-fake runs/d120-off  --out runs/sens_network.md
python src/sensitivity.py runs/d120-fake runs/d120-wrap --out runs/sens_strace.md
```

| File | Dùng cho |
|---|---|
| `runs/<tag>/features.csv` | Hưng: test set cross-dataset (có `Level`, `Group`) |
| `runs/<tag>/errors.csv` | Đăng: error taxonomy FP/FN |
| `runs/<tag>/cost.csv` | bảng chi phí / latency |
| `runs/<tag>/manifest.csv` | data card (SHA256) |
| `runs/*.md` | bảng sensitivity, distribution shift |

## 4. Demo (install → trace → feature → predict)

```bash
sudo OFFLINE=1 NETMODE=fake DECOYS=1 python3 src/main.py sim_packages/mal_sim/sim-exfil-file 60
cat /tmp/dysec_sim_markers/sim-exfil-file.log     # gói đã làm gì
```

Quay màn hình làm video backup. Revert snapshot sau demo.

## Kiểm tra extractor

Đặt raw và processed QUT-DV25 vào `dataset/QUT-DV25-Raw/` và `dataset/QUT-DV25-Processed/`, rồi chạy `python src/validate.py`. Trên 6 gói mẫu, kết quả là 199/216 giá trị khớp tuyệt đối.
