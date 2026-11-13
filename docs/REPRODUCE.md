# Chạy lại các lượt đo NT230 (F1–F6)

Luật của các lượt nằm ở [protocols/PROTOCOL-NT230.md](protocols/PROTOCOL-NT230.md). Mọi lệnh cài gói chỉ chạy **trong VM** (YC_R49: không chạy package độc hại trên máy thật).

## 0. Chuẩn bị VM (một lần, VM còn mạng)

VM: Ubuntu 24.04, kernel 6.8, 4 vCPU, 8 GB RAM. F6 cần thêm một VM Ubuntu 22.04 (kernel 5.15), chuẩn bị y hệt.

```bash
git clone https://github.com/hoangnxm/ML-Based-Malicious-Package-Detection-NT230.git dysec && cd dysec
sudo bash src/scripts/prerequisites.sh            # bpfcc-tools, strace, python3-venv, thư viện ML (requirements.txt)
sudo add-apt-repository -y ppa:deadsnakes/ppa && sudo apt-get install -y python3.8 python3.8-venv
chmod +x src/scripts/*.sh src/variant/*.sh
bash src/scripts/prepare_mirror.sh data/mix-lapE.txt   # wheelhouse/ + 160 file gói độc, 1–2 tiếng
cat wheelhouse/missing.txt                              # những gì không tải được (ghi vào báo cáo)
```

Sau đó **tắt mạng VM** (bỏ tick Connected), tắt Shared Folders, drag & drop, copy/paste, rồi **tạo snapshot** `nt230-ready`.

## 1. Chạy một lượt

Revert về `nt230-ready` trước mỗi lượt. Chặn VM ngủ:

```bash
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
gsettings set org.gnome.desktop.session idle-delay 0
```

Các lượt (mỗi dòng là một lệnh, chạy trong thư mục `dysec`):

```bash
# F1: lượt chính, 270 gói, mạng giả lập (~15 tiếng)
sudo TAG=F1 NETMODE=mirror systemd-inhibit --what=sleep:idle --why=dysec bash src/variant/verify_nt230.sh 2>&1 | tee -a F1.log
# F2: mạng tắt hẳn (~5,5 tiếng)
sudo TAG=F2 NETMODE=off    LIST=data/mix-sens.txt systemd-inhibit --what=sleep:idle --why=dysec bash src/variant/verify_nt230.sh 2>&1 | tee -a F2.log
# F3, F4: thời gian chạy 60 s / 300 s (~4 / ~10 tiếng)
sudo TAG=F3 NETMODE=mirror LIST=data/mix-sens.txt DURATION=60  systemd-inhibit --what=sleep:idle --why=dysec bash src/variant/verify_nt230.sh 2>&1 | tee -a F3.log
sudo TAG=F4 NETMODE=mirror LIST=data/mix-sens.txt DURATION=300 systemd-inhibit --what=sleep:idle --why=dysec bash src/variant/verify_nt230.sh 2>&1 | tee -a F4.log
# F5: dependency, không cài dependency (~5,5 tiếng)
sudo TAG=F5 NETMODE=mirror LIST=data/mix-sens.txt PIPARGS=--no-deps systemd-inhibit --what=sleep:idle --why=dysec bash src/variant/verify_nt230.sh 2>&1 | tee -a F5.log
# F6: OS, chạy trên VM Ubuntu 22.04 (~5,5 tiếng)
sudo TAG=F6 NETMODE=mirror LIST=data/mix-sens.txt systemd-inhibit --what=sleep:idle --why=dysec bash src/variant/verify_nt230.sh 2>&1 | tee -a F6.log
```

- Nếu bị dừng giữa chừng: chạy lại **đúng lệnh đó**, các gói đã đo sẽ được bỏ qua.
- Xong một lượt, terminal in `=== ALL DONE … <TAG>_out.tar.gz sha256 …`.

## 2. Lấy kết quả ra (trước khi revert)

Chỉ chép file `<TAG>_out.tar.gz` ra máy thật (bên trong chỉ có csv, txt, log), rồi kiểm tra mã sha256 có trùng dòng `ALL DONE` không. Sau đó revert VM. Trên máy thật, giải nén vào `results/nt230/<TAG>/`.

## 3. So sánh (máy thật, không cần VM)

```bash
cd results/nt230
for k in F2 F3 F4 F5 F6; do
  python ../../src/variant/compare_runs.py --a F1/F1_ben_scores.csv F1/F1_mal_scores.csv \
      --b $k/${k}_ben_scores.csv $k/${k}_mal_scores.csv --name-a F1 --name-b $k | tee F1_vs_$k.txt
done
```

## 4. Phần chạy được trên máy thật

```bash
pip install -r requirements.txt
python src/evaluate.py            # 4 model trên test QUT-DV25, 6 seed -> results/qut-test/   (--extra: thêm Dummy, LR, KNN)
python src/ablation.py            # ablation 7 nhóm feature -> results/ablation/
python src/authors.py train       # pipeline n-gram theo notebook tác giả -> models/authors/
python src/validate.py            # extractor so với CSV tác giả (cần dataset/QUT-DV25-Raw, -Processed)
```

## 5. So với bài báo

| Bước | Bài báo / dữ liệu QUT-DV25 | Repo |
|---|---|---|
| Máy | Raspberry Pi 4 (ARM), Ubuntu 24.04, kernel 6.8 | VM x86, Ubuntu 24.04, kernel 6.8 |
| Cách cài | gói lành bằng tên (0% tên có `.tar.gz`), gói độc từ `.tar.gz` (99,97%) | giống |
| Python | 3.12 (lành), 3.8 (độc), suy ra từ trace thô | giống |
| pip / setuptools / wheel | 24.3.1 / 75.3.0 / 0.43.0 (lành), 0.45.1 (độc) | `trace.sh` ghim đúng các bản này |
| Lệnh cài | `--break-system-packages --no-build-isolation --no-cache-dir`, lỗi thì thử lại 2 lần | giống |
| Công cụ thu | filetop, opensnoop, tcpstates, strace (quét PID mỗi 1 s), chờ 5 s, 120 s | giống |
| Mạng | mạng riêng của cụm Pi, pip tải từ PyPI thật | `mirror`: pip tải từ chỉ mục giả trên 127.0.0.1 (YC_R49 bắt mạng tắt hoặc giả lập) |
| Model | RF, DT, GB, SVM; chia 70/15/15; RF là model dùng thật | `train.py`, `evaluate.py`; `predict.py`/`main.py` chỉ chạy RF |
