# Protocol các lượt đo NT230 (F1–F6)

File này được commit **trước khi chạy** F1. Sau khi đã thấy số thì không sửa luật bên dưới; muốn đổi thì viết protocol mới và ghi rõ trong báo cáo.

## 1. Mục đích (theo YC_R49)

- "Sandbox/harness tái lập với mạng bị vô hiệu hóa hoặc giả lập": mọi lượt F chạy với `NETMODE=off`, `fake` hoặc `mirror`.
- "Tập trung phân tích tác động của OS, thời gian chạy, dependency và sandbox tới quan sát": mỗi lượt F2–F6 đổi **đúng một** yếu tố so với F1.

## 2. Dữ liệu và cách cài (giữ như QUT-DV25)

- **F1:** `data/mix-lapE.txt`, gồm 270 gói: 110 lành (`data/benign-lapD.txt`, không có trong QUT-DV25) và 160 độc (`data/malicious-lapC.txt`, mỗi họ tên một gói, lấy từ tập test của tác giả). Thứ tự xen kẽ cố định, giống lần E.
- **F2–F6:** `data/mix-sens.txt`, gồm 100 dòng (50 lành, 50 độc) lấy từ `mix-lapE.txt` bằng `src/data/make-mix-sens.py` (seed 230), giữ thứ tự gốc.
- Gói lành cài **bằng tên** với `python3` (3.12). Gói độc cài **từ file `.tar.gz`** với `python3.8`. Lý do: trong `dataset/QUT-DV25.csv`, 0% tên gói lành và 99,97% tên gói độc kết thúc bằng `.tar.gz`.
- Gói độc tải từ pypi_malregistry, ngay trong VM, bằng `src/scripts/prepare_mirror.sh`. Script này đọc dependency của gói độc một cách tĩnh và không chạy code trong gói.

## 3. Các lượt

| Lượt | Danh sách | NETMODE | Thời gian | pip | Máy | Yếu tố được đo (so với F1) |
|---|---|---|---|---|---|---|
| F1 | mix-lapE (270) | mirror | 120 s | như tác giả | VM Ubuntu 24.04, kernel 6.8 | lượt chính |
| F2 | mix-sens (100) | off | 120 s | như tác giả | như F1 | sandbox: mạng tắt hẳn |
| F3 | mix-sens | mirror | 60 s | như tác giả | như F1 | thời gian chạy |
| F4 | mix-sens | mirror | 300 s | như tác giả | như F1 | thời gian chạy |
| F5 | mix-sens | mirror | 120 s | `--no-deps` | như F1 | dependency |
| F6 | mix-sens | mirror | 120 s | như tác giả | VM Ubuntu 22.04, kernel 5.15 | OS |

Thêm một mốc tham khảo cho sandbox: lần C và D (mạng NAT thật, cùng các gói, đo riêng từng nhãn trên cùng VM). Mốc này **không** cùng thứ tự với F1, nên chỉ dùng làm tham khảo và phải ghi rõ khác biệt.

## 4. Cố định

- **Model:** `models/Random-Forest.pkl` (sha256 `02eaa61f…`). Hai biến thể train lại bằng `src/variant/train_variant.py` lúc bắt đầu mỗi lượt; script in sha256 vào log. Ngưỡng 0,5.
- **Lần đo bị loại** (giống lần C/D/E): probe eBPF dừng sớm sau tối đa 2 lần chạy lại; Attach_Delay trên 10 giây; không có thời gian cài; gói độc mà pip lỗi trước bước build (xem `score_mal.py`).
- **Không chạy lại** để lấy số đẹp hơn. Lượt nào dừng giữa chừng thì chạy tiếp bằng đúng lệnh cũ (script tự bỏ qua gói đã đo xong).

## 5. Phân tích

- Mỗi lượt: FPR trên gói lành, recall trên gói độc, Wilson CI 95%, cho cả ba model (`score_benign.py`, `score_mal.py`).
- F2–F6 so với F1 **trên cùng các gói** (chỉ tính gói hợp lệ ở cả hai lượt): `src/variant/compare_runs.py`, McNemar chính xác hai phía trên các gói bị đổi kết luận.
- Có 5 phép so (F2–F6), nên một yếu tố chỉ được ghi là "làm đổi kết luận" khi p < 0,01 (Bonferroni 0,05/5). Không đạt thì ghi "không thấy khác biệt với cỡ mẫu này", kèm CI. Không đảo thành "không ảnh hưởng".
- Lượt nào cũng báo cáo, kể cả khi không thấy khác biệt.

## 6. Giới hạn biết trước

- F2–F6 chỉ có 50 gói mỗi nhãn, nên CI rộng khoảng ±10–14 điểm phần trăm. Phép so cặp với F1 bù được một phần.
- `mirror` phục vụ gói từ wheelhouse trên 127.0.0.1, nên trace không có truy vấn DNS và kết nối Internet như khi tác giả cài trên mạng thật.
- Gói độc nào có dependency không tải được thì ghi trong `wheelhouse/missing.txt`. Pip cài lỗi thì bị loại theo luật ở mục 4.
