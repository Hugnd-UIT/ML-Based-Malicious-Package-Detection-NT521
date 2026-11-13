# Data card — bộ trace tự thu (NT230, đề R49 DySec)

Bộ dữ liệu nhỏ do nhóm tự thu bằng đúng quy trình DySec/QUT-DV25 (eBPF + strace lúc `pip install`). Dùng để kiểm tra model train trên QUT-DV25 có chạy được trên trace thu ở môi trường khác hay không (cross-dataset), và để đo ảnh hưởng của cấu hình thu trace (sensitivity).

## Thành phần

| Nhóm | Số gói | Nhãn | Nguồn |
|---|---|---|---|
| `benign-pypi` | 12 | 0 | Gói phổ biến trên PyPI, cài bằng tên |
| `benign-hook` | 3 | 0 | Gói sạch có chạy code lúc cài, do Đăng viết (`sim_packages/benign_hook`) |
| `mal-sim` | 8 | 1 | Gói **mô phỏng vô hại** các TTP độc, do Đăng viết (`sim_packages/mal_sim`) |
| `mal-qut` | 3 | 1 | Gói độc thật lấy từ QUT-DV25 (aaiohttp, aihottp, aiohhttp), chỉ có ở `results/runs/w3` |

Danh sách đầy đủ và nhãn: [data/packages.csv](../../data/packages.csv). Định nghĩa nhãn và TTP của từng gói mô phỏng: tài liệu của Đăng (`DinhNghiaNhan_DacTrung_DySec.docx`, `GoiMoPhong_DySec.docx`).

Gói `mal-sim` không chứa payload thật: chỉ đọc file mồi `~/fake_secret.txt`, chỉ kết nối `127.0.0.1`, và ghi marker vào `/tmp/dysec_sim_markers/`.

## Các lần thu (run)

Mỗi run nằm trong `results/runs/<tag>/`. Raw trace không đẩy lên git vì quá nặng (100–200 MB/run), nhưng SHA256 của từng file nằm trong `results/runs/<tag>/manifest.csv`.

| Run | Ngày | Gói | Thời lượng | Mạng | strace | Ghi chú |
|---|---|---|---|---|---|---|
| `w2` | 29/09/2026 | 5 benign-pypi | 120 s | thật | poll 1 s | script tuần 2 |
| `w3` | 01/10/2026 | 5 benign-pypi + 3 mal-qut | 120 s | thật (benign) / offline (mal-qut) | poll 1 s | script tuần 3 |
| `d60-fake`, `d120-fake`, `d300-fake` | 10/2026 | 21 gói của packages.csv | 60 / 120 / 300 s | fake | poll 1 s | xem [REPRODUCE](../../docs/REPRODUCE.md) |
| `delayed-120`, `delayed-300` | 10/2026 | sim-delayed (packages_delayed.csv) | 120 / 300 s | fake | poll 1 s | thử gói kích hoạt trễ |
| `d120-wrap` | 10/2026 | 21 gói | 120 s | fake | wrap | so poll với wrap |

Run mới thì `trace.sh` tự ghi cấu hình vào `traces/<gói>/meta.env`, và `python src/manifest.py results/runs/<tag>` in ra tóm tắt môi trường để chép vào bảng trên.

## Môi trường (run w2, w3)

| Mục | Giá trị |
|---|---|
| OS | Ubuntu (VM x86_64), kernel `6.8.0-142-generic` |
| Python | 3.12 (benign), 3.8 (mal-qut, cài offline từ `wheelhouse/python3.8`) |
| pip | 26.2.1 |
| Probe | `filetop-bpfcc 5`, `opensnoop-bpfcc -d 10`, `tcpstates-bpfcc` (bpfcc-tools), `strace -f -ff -s 4096 -t -v` |
| Chờ trước khi cài | 5 s (giống script gốc QUT-DV25) |
| Cache pip | tắt (`--no-cache-dir`) |

## Đặc trưng

36 feature giống hệt QUT-DV25 (xem [docs/36-features.md](../../docs/36-features.md)), trích bằng `src/extract.py`. Đối chiếu với CSV gốc của tác giả trên 6 gói mẫu: **199/216 giá trị khớp tuyệt đối (92.1%)**. TCP, Filetop, Install, SysCall khớp 100%. Opensnoop lệch vài đơn vị trên vài nghìn (raw trace tác giả công bố có thể không trùng hẳn bản họ dùng để tính CSV). Pattern lệch do thứ tự các n-gram có cùng số lần xuất hiện.

File kết quả của mỗi run (`python src/collect.py results/runs/<tag>`):

- `features.csv`: 36 feature + `Level` (nhãn) + `Group`
- `predictions.csv`, `errors.csv`: dự đoán của 7 model, và riêng các ca sai (FP/FN)
- `cost.csv`: thời gian cài/trace, dung lượng log, thời gian trích feature, latency predict

## Hạn chế đã biết

1. **Môi trường khác QUT-DV25.** Opensnoop/tcpstates/filetop bắt toàn hệ thống, không lọc theo PID, nên tiến trình nền của VM (desktop, firefox, snap) đi thẳng vào feature. Ví dụ `Sys_Access` của nhóm khoảng 100 trong khi median benign của QUT-DV25 là 1095. `Remote_IP_Address_Access` là 2–4, còn QUT-DV25 là 49.
2. **strace gắn trễ.** `monitor.sh` quét PID mỗi 1 s, nên gói cài nhanh (requests) bị mất toàn bộ lời gọi mạng (`Network_Operations = 0`). Có chế độ `STRACE=wrap` để so sánh.
3. **Lặp lại không ổn định.** Cùng 5 gói, cùng script, thu 2 lần (w2, w3): feature Opensnoop khác nhau tới 10 lần và Random-Forest đổi kết luận ở 2/5 gói ([results/runs/sensitivity_w2_vs_w3.md](results/runs/sensitivity_w2_vs_w3.md)).
4. **Quy mô nhỏ.** 21 gói (cộng 8 gói ở w2/w3), chỉ đủ để phân tích từng ca, không đủ để kết luận thống kê.
5. **Gói mô phỏng không phải mã độc thật.** Chúng tái tạo dấu vết hệ thống của TTP, không tái tạo được độ phức tạp (obfuscation nhiều lớp, anti-sandbox) của mẫu thật.

## License và sử dụng

Trace của gói benign và gói mô phỏng được dùng cho mục đích học thuật. Không phát tán raw trace của gói độc thật (`mal-qut`), và không đăng gói mô phỏng lên PyPI.
