# Chạy F1–F6 chia cho 3 người (Hoàng, Đăng, Hưng)

Phụ lục của [PROTOCOL-NT230.md](PROTOCOL-NT230.md). **Không đổi luật đo**: danh sách gói, thời lượng, `NETMODE`, luật loại trừ, model và cách phân tích vẫn như protocol. Phụ lục chỉ ghi thêm ai đo phần nào và gộp kết quả ra sao. File này được commit **trước khi chạy** F1; sau khi đã thấy số thì không sửa luật bên dưới.

## 1. Phân chia

Danh sách gói đã chia sẵn trong [data/split/](../../data/split/README.md), mỗi người một folder:

| Người | Folder | F1 (`mix-lapE.txt`) | F2–F6 (`mix-sens.txt`) | Giờ ước tính cả F1–F6 |
|---|---|---|---|---|
| Hoàng | `data/split/Hoang/` | 91 gói | 33 gói | ~15,1 |
| Đăng | `data/split/Dang/` | 90 gói | 35 gói | ~15,7 |
| Hưng | `data/split/Hung/` | 89 gói | 32 gói | ~14,7 |

Một người chạy một mạch F1 → F2 → F3 → F4 → F5 trên VM Ubuntu 24.04, rồi F6 trên VM Ubuntu 22.04, **chỉ trên phần của mình**, không cần đợi hai người kia giữa các lượt.

Một gói luôn do cùng một người đo ở mọi lượt (F2–F6 là tập con của F1 và được chia theo cùng người). Vì vậy so cặp F1 với Fk không lẫn khác biệt giữa các máy. Hai VM của một người phải nằm trên **cùng một máy thật**.

Giờ ước tính lấy từ [REPRODUCE.md](../REPRODUCE.md) (Hoàng đã đo: F1 ~15 h, F2 ~5,5 h, F3 ~4 h, F4 ~10 h, F5 ~5,5 h, F6 ~5,5 h, tổng ~45,5 h nếu một người làm hết), nhân theo số gói của từng người. Chưa tính gói đo lại (tối đa 2 lần), dựng VM và chép kết quả.

## 2. Yêu cầu kỹ thuật

**Máy thật (mỗi người)**
- VMware Workstation 17, RAM từ 16 GB, ổ trống khoảng 40 GB cho mỗi VM (con số của lần E; có VM thứ hai cho F6 thì cộng thêm). Cắm sạc, mạng ổn định lúc chuẩn bị.
- Chặn máy thật ngủ: `powercfg /change standby-timeout-ac 0` và `powercfg /change hibernate-timeout-ac 0` (PowerShell quyền Administrator).
- Chỉ bật **một VM** tại một thời điểm và không chạy việc nặng khác trên máy thật trong lúc đo. Các gói chạy lần lượt một gói một lúc, vì filetop/opensnoop/tcpstates bắt toàn hệ thống; gói khác chạy cùng lúc sẽ lẫn vào trace.

**VM**
- F1–F5: Ubuntu 24.04, kernel 6.8, 4 vCPU, 8 GB RAM. F6: Ubuntu 22.04, kernel 5.15, cấu hình y hệt. Không tăng vCPU/RAM.
- Cài theo [REPRODUCE.md](../REPRODUCE.md) mục 0: `prerequisites.sh` (bpfcc-tools, strace, python3-venv, thư viện ML), `python3.8` và `python3.8-venv` từ deadsnakes.
- **`python3` phải là 3.12 trên cả hai VM** (gói lành cài bằng python3 theo protocol, và `wheelhouse/python3/` được tải bằng 3.12). Kiểm: `python3 --version`. Ubuntu 22.04 mặc định là 3.10; nếu không phải 3.12 thì gói có phần biên dịch không tìm thấy wheel phù hợp, bị loại, và yếu tố Python lẫn vào yếu tố OS của F6.
- Thư viện đúng `requirements.txt`: `scikit-learn==1.9.0`, `pandas==3.0.3`, `numpy==2.4.6`, `joblib==1.5.3`. Kiểm: `pip3 list 2>/dev/null | grep -Ei "^(scikit-learn|pandas|numpy|joblib) "`. Lệch phiên bản là nguồn đã gây chênh lệch Run A/B trước đây.

**Model**: dùng bản đã commit, **không train lại**. `verify_nt230.sh` chỉ train khi thiếu file `.pkl`; nếu thấy dòng `[+] drop_g1g2 ... saved` trong log thì file bị thiếu, hash sẽ lệch, dừng và báo. Ba file phải có đúng sha256 ghi trong [expected_model_sha256.txt](expected_model_sha256.txt). Kiểm trong VM, ở thư mục gốc repo, phải ra 3 dòng `OK`:

```bash
sha256sum -c docs/protocols/expected_model_sha256.txt
```

Bảng hash trong `CHAY_KIEM_CHUNG_lapE.md` là của lần E, không dùng cho F1–F6.

**An toàn** (cả F1 lẫn F2–F6 đều có gói độc thật: 160 gói ở F1 và 50 gói ở F2–F6, chia cho ba người)
- Tắt Shared Folders, drag & drop, copy/paste (Settings > Options). Script tự dừng nếu thấy hgfs.
- Tắt mạng VM (bỏ tick Connected) sau khi chuẩn bị xong. `NETMODE=off|mirror` còn chặn mọi kết nối ra ngoài ngoài loopback bằng iptables bên trong VM.
- Không lưu đăng nhập GitHub trong VM. Nếu đã có: `rm -f ~/.git-credentials /root/.git-credentials; git config --global --unset-all credential.helper` (giống `verify_mal.sh`).
- **Revert về snapshot `nt230-ready` trước mỗi lượt và sau lượt cuối.** Chỉ chép ra `<TAG>_out.tar.gz` (bên trong chỉ có csv, txt, log).
- Không chạy gói độc trên máy thật. Mọi lệnh `verify_nt230.sh` chỉ chạy trong VM.

## 3. Chuẩn bị (làm một lần, VM còn mạng)

Thứ tự bắt buộc, vì snapshot phải chứa đúng code và dữ liệu:

1. **Chốt một commit chung**: commit và push `data/split/`, `src/data/split-mix-3.py`, `src/variant/merge_scores.py` và file này. Cả ba `git pull` về đúng commit đó. Kiểm: `git log --oneline -1` giống nhau.
2. **Một người dựng wheelhouse** (đề xuất Hoàng), để cả ba dùng cùng một bản phụ thuộc (tải riêng ở các thời điểm khác nhau có thể ra phiên bản khác):
   ```bash
   bash src/scripts/prepare_mirror.sh data/mix-lapE.txt     # 1–2 tiếng, VM còn mạng
   cat wheelhouse/missing.txt                                # gói không tải được; ghi vào báo cáo
   du -sh wheelhouse                                         # xem dung lượng trước khi gửi
   tar -czf ../nt230-wheelhouse.tgz wheelhouse *.tar.gz      # wheelhouse + 160 file gói độc ở thư mục gốc repo
   sha256sum ../nt230-wheelhouse.tgz
   ```
3. **Hai người còn lại nhận file `.tgz`**, kiểm sha256 trùng, rồi giải nén vào thư mục gốc repo **trong mỗi VM** (`tar -xzf nt230-wheelhouse.tgz -C ~/dysec`). Kiểm: `ls wheelhouse` có `python3` và `python3.8`; `ls *.tar.gz | wc -l` bằng số của người dựng. (Chép file vào VM lúc còn mạng hoặc Shared Folders, trước bước 5.)
4. Trên **cả hai VM** (24.04 và 22.04): kiểm đủ các mục ở phần 2 (`python3 --version`, phiên bản thư viện, `sha256sum -c docs/protocols/expected_model_sha256.txt`), và `sha256sum data/split/<Tên>/*.txt | cut -c1-12` trùng bảng trong `data/split/README.md`.
5. Tắt mạng VM, tắt Shared Folders/drag & drop/copy-paste, **tạo snapshot `nt230-ready`** cho từng VM.

## 4. Chạy (mỗi người, trong thư mục `dysec`)

Thay `<Tên>` bằng `Hoang`, `Dang` hoặc `Hung`. Revert về `nt230-ready` trước **mỗi** lệnh. Chặn VM ngủ một lần sau mỗi lần revert:

```bash
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
gsettings set org.gnome.desktop.session idle-delay 0
```

Trên VM 24.04:

```bash
# F1: lượt chính, mạng giả lập, 120 s
sudo TAG=F1 NETMODE=mirror LIST=data/split/<Tên>/mix-lapE.txt systemd-inhibit --what=sleep:idle --why=dysec bash src/variant/verify_nt230.sh 2>&1 | tee -a F1.log
# F2: mạng tắt hẳn
sudo TAG=F2 NETMODE=off LIST=data/split/<Tên>/mix-sens.txt systemd-inhibit --what=sleep:idle --why=dysec bash src/variant/verify_nt230.sh 2>&1 | tee -a F2.log
# F3, F4: thời gian chạy 60 s và 300 s
sudo TAG=F3 NETMODE=mirror DURATION=60  LIST=data/split/<Tên>/mix-sens.txt systemd-inhibit --what=sleep:idle --why=dysec bash src/variant/verify_nt230.sh 2>&1 | tee -a F3.log
sudo TAG=F4 NETMODE=mirror DURATION=300 LIST=data/split/<Tên>/mix-sens.txt systemd-inhibit --what=sleep:idle --why=dysec bash src/variant/verify_nt230.sh 2>&1 | tee -a F4.log
# F5: không cài dependency
sudo TAG=F5 NETMODE=mirror PIPARGS=--no-deps LIST=data/split/<Tên>/mix-sens.txt systemd-inhibit --what=sleep:idle --why=dysec bash src/variant/verify_nt230.sh 2>&1 | tee -a F5.log
```

Trên VM 22.04 (cùng máy thật):

```bash
# F6: đổi OS
sudo TAG=F6 NETMODE=mirror LIST=data/split/<Tên>/mix-sens.txt systemd-inhibit --what=sleep:idle --why=dysec bash src/variant/verify_nt230.sh 2>&1 | tee -a F6.log
```

- Dòng đầu log phải có đúng `NETMODE`, `DURATION`, `PIPARGS`, `LIST` của lượt đó và `commit` chung. Dòng `=== malicious archives present: x/y` cho biết số gói độc có file (thiếu thì gói đó bị bỏ qua, ghi vào báo cáo).
- Bị dừng giữa chừng: chạy lại **đúng lệnh đó**, các gói đã đo được bỏ qua. Không dựng lại VM, không revert giữa chừng.
- **Không chạy lại để lấy số đẹp hơn.** Chỉ có luật đo lại của protocol (probe chết, `Attach_Delay` trên 10 giây), script tự làm.

## 5. Lấy kết quả ra (TRƯỚC khi revert)

Cuối mỗi lượt terminal in `=== ALL DONE … <TAG>_out.tar.gz sha256 …`. Trên máy thật (PowerShell), thay phần trong ngoặc nhọn; cách này giống lần E:

```powershell
& "C:\Program Files (x86)\VMware\VMware Workstation\vmrun.exe" -T ws -gu <user VM> -gp <mật khẩu VM> CopyFileFromGuestToHost "<đường dẫn .vmx>" /home/<user VM>/dysec/F1_out.tar.gz "<thư mục nhận>\F1_<Tên>_out.tar.gz"
Get-FileHash "<thư mục nhận>\F1_<Tên>_out.tar.gz"
```

Hash phải trùng dòng `ALL DONE`. Chỉ chép đúng file `.tar.gz` này. Xong mới revert. Đặt tên `F<k>_<Tên>_out.tar.gz` để ba người gửi vào cùng một chỗ mà không đè nhau.

## 6. Gộp và so sánh (một máy thật, không cần VM)

```bash
# giải nén, mỗi người một folder con (tên folder = tên người)
for k in F1 F2 F3 F4 F5 F6; do for p in Hoang Dang Hung; do
  mkdir -p results/nt230/$k/$p && tar -xzf "<thư mục nhận>/${k}_${p}_out.tar.gz" -C results/nt230/$k/$p
done; done

# gộp theo từng lượt
for k in F1 F2 F3 F4 F5 F6; do
  python src/variant/merge_scores.py --tag $k --out results/nt230/$k \
      results/nt230/$k/Hoang results/nt230/$k/Dang results/nt230/$k/Hung | tee results/nt230/$k/${k}_pooled_summary.txt
done

# so F2–F6 với F1 (như REPRODUCE.md mục 3)
cd results/nt230
for k in F2 F3 F4 F5 F6; do
  python ../../src/variant/compare_runs.py --a F1/F1_ben_scores.csv F1/F1_mal_scores.csv \
      --b $k/${k}_ben_scores.csv $k/${k}_mal_scores.csv --name-a F1 --name-b $k | tee F1_vs_$k.txt
done
```

`merge_scores.py` ghép các `<TAG>_ben_scores.csv` và `<TAG>_mal_scores.csv` mà **mỗi người đã chấm sẵn trong VM** của mình, rồi tính FPR/recall gộp với Wilson 95%. Nó dừng nếu một gói xuất hiện ở hai người (chia chồng nhau) hoặc thiếu file.

**Không chấm lại bằng `score_benign.py` hay `score_mal.py` trên máy thật.** `score_mal.py` đọc `traces/<gói>/…_install_log.txt`, chỉ có trong VM; trên máy thật các gói độc mà pip báo lỗi sau khi bước build đã chạy sẽ bị loại nhầm.

Máy gộp cần `pip install -r requirements.txt` (như REPRODUCE.md mục 4).

**Kiểm tra trước khi tin số.** Chạy trong `results/nt230`, mỗi lệnh cho một lượt (thay `F1` bằng lượt khác):

1. Cùng cấu hình máy, OS, kernel và commit. Lệnh này chỉ được ra **một dòng**:
   ```bash
   grep -h "=== START" F1/*/F1.log | awk -F' [|] ' '{print $4" | "$5" | "$6" | "$7}' | sort -u
   ```
2. Cùng model. Không được có dòng nào khác với file expected (không in gì ngoài chữ `model khớp`):
   ```bash
   grep -h "\.pkl" F1/*/F1.log | sort -u | diff - ../../docs/protocols/expected_model_sha256.txt && echo "model khớp"
   ```
3. Số gói đã đo của từng người (dòng `traced` do `merge_scores.py` in) bằng bảng ở `data/split/README.md`. F1 gồm 37+54, 37+53, 36+53 (lành+độc) cho Hoàng, Đăng, Hưng; F2–F6 gồm 15+18, 19+16, 16+16.
4. Tỉ lệ bị loại của ba người (cũng do `merge_scores.py` in) nên gần nhau. Script in ghi chú khi hai người lệch từ 10 điểm phần trăm trở lên; đó chỉ là gợi ý xem lại máy chậm hay đang chạy việc khác, không phải luật của protocol. `Attach_Delay` phụ thuộc tốc độ máy thật nên máy chậm hơn bị loại nhiều hơn.
5. So `F<k>_ben_summary.txt` và `F<k>_mal_summary.txt` trong folder của từng người. Nếu FPR hoặc recall riêng của một người lệch hẳn hai người kia, ghi vào phần giới hạn của báo cáo (mỗi người đo một phần ba gói khác nhau).

## 7. Việc cần chốt trước khi chạy F1

1. **`PROTOCOL-NT230.md` mục 4 còn ghi** "Hai biến thể train lại bằng `train_variant.py` lúc bắt đầu mỗi lượt". Từ commit `c8a5955`, `verify_nt230.sh` dùng model đã commit và chỉ train khi thiếu file. Cần sửa mục 4 cho khớp (Hoàng) trước khi chạy, để protocol đúng với cái được chạy.
2. Xác nhận cách đặt `python3` = 3.12 trên VM Ubuntu 22.04 (phần 2) và ghi lại lệnh đã dùng.
3. Chốt ai dựng wheelhouse, và gửi file `.tgz` bằng cách nào (xem dung lượng bằng `du -sh wheelhouse`).
4. `verify.sh`, `verify_fresh.sh`, `verify_lapd.sh`, `verify_mal.sh`, `verify_mix.sh` vẫn gọi `train_variant.py` vô điều kiện và sẽ ghi đè các file model đã commit. **Không chạy 5 script đó** trong lúc làm F1–F6 (hoặc `git checkout -- models/variant/` rồi kiểm lại hash sau khi chạy).
