# Chia danh sách gói cho 3 người chạy F1–F6

Mỗi người một folder, mỗi folder có đúng 2 file cùng tên với file gốc:

| Folder | Người | `mix-lapE.txt` (dùng cho F1) | `mix-sens.txt` (dùng cho F2–F6) |
|---|---|---|---|
| `Hoang/` | Hoàng | 91 gói (37 lành, 54 độc) | 33 gói (15 lành, 18 độc) |
| `Dang/` | Đăng | 90 gói (37 lành, 53 độc) | 35 gói (19 lành, 16 độc) |
| `Hung/` | Hưng | 89 gói (36 lành, 53 độc) | 32 gói (16 lành, 16 độc) |
| Tổng | | 270 | 100 |

## Luật chia (không ngẫu nhiên, chốt trước khi chạy)

1. Đi qua `data/mix-lapE.txt` theo thứ tự gốc, đếm riêng lớp lành (`B`) và lớp độc (`M`). Dòng thứ k của một lớp (k bắt đầu từ 0) thuộc người thứ `k mod 3`, theo thứ tự Hoàng, Đăng, Hưng. Mỗi người giữ nguyên thứ tự xen kẽ của lần E và có tỉ lệ lành/độc gần bằng nhau.
2. `data/mix-sens.txt` là tập con của `data/mix-lapE.txt`. Gói nào của nó thuộc về người nào ở bước 1 thì người đó đo gói đó ở F2–F6. Nhờ vậy **một gói luôn do cùng một người đo ở cả F1 và F2–F6**, nên so cặp F1 với Fk chỉ khác nhau ở yếu tố đang kiểm, không lẫn với khác biệt giữa các máy.

Không sửa tay các file trong folder này. Muốn sinh lại: `python3 src/data/split-mix-3.py` (kết quả giống hệt, vì không có ngẫu nhiên).

## Mã kiểm tra (12 ký tự đầu của sha256)

| Folder | `mix-lapE.txt` | `mix-sens.txt` |
|---|---|---|
| `Hoang/` | `6b69d37d4eef` | `742869d3630e` |
| `Dang/` | `81d95352877a` | `9c0e022e6295` |
| `Hung/` | `1ce92525a3c8` | `ed2208063718` |

Kiểm trong VM: `sha256sum data/split/<Tên>/*.txt | cut -c1-12`. File dùng LF; `.gitattributes` của repo không ép `*.txt`, nên nếu clone trên Windows với `core.autocrlf=true` file sẽ thành CRLF và mã sha256 sẽ lệch. Chỉ kiểm trong VM Linux.
