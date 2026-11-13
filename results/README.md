# Số liệu

| Thư mục | Nội dung | Sinh bằng |
|---|---|---|
| `qut-test/` | 4 model trên tập test QUT-DV25 (6 seed), confusion matrix, ROC | `python src/evaluate.py` |
| `ablation/ablation.csv` | Ablation theo 7 nhóm feature (G1–G7), 5 seed | `python src/ablation.py` |
| `nt230/<TAG>/` | Các lượt F1–F6: `*_results.csv`, `*_features.csv`, `*_scores.csv`, `*_summary.txt`, log | `src/variant/verify_nt230.sh` (trong VM), xem [docs/REPRODUCE.md](../docs/REPRODUCE.md) |
| `nt230/F1_vs_Fk.txt` | So cặp từng lượt với F1 (Wilson CI, McNemar) | `src/variant/compare_runs.py` |

`nt230/` chưa có: các lượt F chưa chạy.

Các lượt thu trước 13/11/2026 (21 gói, `trace.sh` cũ, có gói mô phỏng) không còn trong repo. Bản lưu nằm ở `DOAN/runs_core/` và `DOAN/_bo_khoi_repo/` trên máy Hoàng, vẫn xem được trong lịch sử git.
