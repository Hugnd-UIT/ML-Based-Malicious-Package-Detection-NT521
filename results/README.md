# Số liệu

| Thư mục | Nội dung | Sinh bằng |
|---|---|---|
| `qut-test/` | Kết quả 4 model trên tập test QUT-DV25 (6 seed), confusion matrix, ROC | `python src/evaluate.py` |
| `ablation/ablation.csv` | Ablation theo 7 nhóm feature (G1–G7), 5 seed | `python src/ablation.py` |
| `runs/<tag>/` | Mỗi lượt thu trace trên VM: `features.csv`, `predictions.csv`, `errors.csv`, `cost.csv`, `manifest.csv` (SHA256 raw trace) | `trace_batch.sh` → `collect.py`, `manifest.py` |

Raw trace (`runs/<tag>/traces/`, `outputs/`) không đẩy lên git. SHA256 của từng file nằm trong `manifest.csv`.

## Các lượt đã thu

**Tất cả các lượt dưới đây thu bằng `trace.sh` cũ (trước 13/11/2026).** Bản đó chưa có các sửa của NT521: cờ pip `--no-build-isolation` của tác giả, ghim pip 24.3.1 / setuptools 75.3.0, dọn pip và monitor còn sót, đo Attach_Delay. Nên chỉ dùng chúng để giải thích xu hướng, không đặt cạnh số mới như cùng một điều kiện.

| Tag | Gói | Cách cài | Mạng | strace | Thời lượng |
|---|---|---|---|---|---|
| `w2`, `w3` | 5 benign (+3 độc thật ở w3) | tên gói / file | thật (w3: gói độc offline) | poll | 120 s |
| `d60-fake`, `d120-fake`, `d300-fake` | 21 (d60/d300: 8) | wheel (PyPI), thư mục (mô phỏng) | fake, offline | poll | 60 / 120 / 300 s |
| `delayed-120`, `delayed-300` | sim-delayed | thư mục | fake, offline | poll | 120 / 300 s |
| `d120-wrap` | 21 | wheel / thư mục | fake, offline | wrap | 120 s |
| `paper-d120` | 21 | `.tar.gz` | fake, offline | poll | 120 s |
| `paper-pypi-d120` | 21 | `.tar.gz` | pypi (dependency tải online) | poll | 120 s |

Các file `.md` ở đây (`sens_duration.md`, `sensitivity_w2_vs_w3.md`) so các lượt trên với nhau.

Kết quả lần A–E (gói lành/độc thật, model biến thể bỏ G1+G2) chạy ở repo [DySec-NT521](https://github.com/hoangnxm/DySec-NT521). File CSV của các lần đó chưa chép vào đây.
