# An toàn khi thu trace

## Nguyên tắc

- **Không bao giờ cài gói độc trên máy thật.** Chỉ cài trong VM Ubuntu đã có snapshot sạch.
- **NT230 dùng gói mô phỏng vô hại** (`sim_packages/`, do Đăng viết) thay cho gói độc thật. Gói mô phỏng chỉ đọc file mồi, chỉ kết nối `127.0.0.1`, chỉ chạy `echo hello`.
- **Mạng tắt, giả lập hoặc chỉ mở PyPI** khi cài gói mô phỏng: `NETMODE=off`, `fake` hoặc `pypi`. `pypi` chỉ mở DNS và HTTPS tới `pypi.org`, `files.pythonhosted.org` để pip tải dependency như bài báo. Cả ba chế độ dùng iptables chặn mọi kết nối ra ngoài còn lại, chỉ chừa loopback. `fake` và `pypi` bật thêm server giả `127.0.0.1:9999` (C2) và `127.0.0.1:8000` (HTTP).
- **Không đẩy lên git:** gói độc thật, raw trace của gói độc thật, thư mục `sim_packages/` dưới dạng cài được. `.gitignore` đã chặn `sim_packages/`, `wheelhouse/`, `runs/*/traces/`, `runs/*/outputs/`.

## Quy trình

### Gói mô phỏng và gói benign (chạy hàng loạt)

1. Revert VM về snapshot sạch.
2. Khi còn mạng: chạy `prepare_wheelhouse.sh` một lần để tải sẵn wheel.
3. Chạy `trace_batch.sh` với `OFFLINE=1 NETMODE=fake` (hoặc `off`). Giữa 2 gói, script tự dọn tiến trình nền của `sim-delayed`, marker, file `/tmp/dysec_dropped_payload.py`, `/tmp/benign-cext_build`, `~/.config/benign-config`.
4. Copy `runs/<tag>/` ra máy thật: chỉ có log và CSV, không có code chạy được.
5. Revert snapshot.

### Gói độc thật (chỉ khi thật sự cần, ví dụ đối chiếu với QUT-DV25)

1. Snapshot, ngắt card mạng của VM ở phần mềm ảo hoá.
2. Chạy từng gói một: `sudo OFFLINE=1 NETMODE=off PYTHON=python3.8 ./src/scripts/trace.sh <file.tar.gz>`.
3. Lấy log ra, **revert snapshot ngay sau mỗi gói.**
4. Không chạy gói độc thật bằng `trace_batch.sh`.

## Kiểm tra nhanh trước khi chạy

- [ ] VM đã có snapshot sạch, đang ở snapshot đó
- [ ] `sudo iptables -L OUTPUT` không còn chain `DYSEC_NET` sót lại từ lần trước
- [ ] Không có thư mục chia sẻ (shared folder) ghi được từ VM ra máy thật trong lúc cài
- [ ] Chạy gói mô phỏng với `NETMODE=off`, `fake` hoặc `pypi`, không dùng `real`
