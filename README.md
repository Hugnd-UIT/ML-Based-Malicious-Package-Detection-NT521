# A Machine Learning-Based Dynamic Analysis for Detecting Malicious Packages in PyPI Ecosystem (NT521)

Hệ thống phân tích động (Dynamic Analysis) dựa trên nhân Linux (eBPF & Strace) kết hợp Machine Learning để phát hiện gói mã độc trên hệ sinh thái PyPI.

---

## Quy trình kiểm thử thực tế (End-to-End Pipeline)
---

### Yêu cầu môi trường
- Hệ điều hành: **Ubuntu 22.04 / 24.04 (x86_64)** chạy trên VMware hoặc VirtualBox.
- Quyền quản trị viên (`sudo`).

---

### Bước 0: Cài đặt công cụ ban đầu (Chỉ chạy 1 lần duy nhất)

Mở terminal trong thư mục dự án trên máy ảo Linux:

```bash
sudo bash src/scripts/prerequisites.sh
chmod +x src/scripts/trace.sh src/scripts/monitor.sh
```

---

### Bước 1: Thu thập trace động khi cài đặt gói

Chạy `trace.sh` với tên gói cần kiểm tra (ví dụ: `requests`, thời gian giám sát 30 giây):

```bash
sudo bash src/scripts/trace.sh requests 30
```

- Hệ thống tự động tạo môi trường ảo độc lập (`env/requests/`), bật đồng thời các probe eBPF (`opensnoop`, `tcpstates`, `filetop`) và `strace` để giám sát toàn bộ lời gọi hệ thống khi `pip install` thực thi.
- Dữ liệu thô được lưu vào:
  - `traces/requests/`: Chứa các log eBPF và nhật ký cài đặt.
  - `outputs/requests/`: Chứa log các system call chi tiết.

---

### Bước 2: Bóc tách 36 đặc trưng ra file CSV bằng chứng

Sử dụng `extract.py` để phân tích các log thô vừa thu được và xuất ra file CSV bằng chứng thực nghiệm:

```bash
python src/extract.py --pkg requests --out requests_evidence.csv
```

- Tạo ra file `requests_evidence.csv` gồm đúng 36 đặc trưng động (SEF) thuộc 6 nhóm hành vi (Opensnoop, TCP, Filetop, Install, SysCall, Pattern).
- File CSV này có thể mở bằng Excel để kiểm tra và lưu trữ làm bằng chứng số liệu.

---

### Bước 3: Đưa file CSV bằng chứng vào 4 mô hình AI dự đoán

Nạp file CSV bằng chứng vào `predict.py`:

```bash
python src/predict.py requests_evidence.csv
```

Hệ thống sẽ tiền xử lý dữ liệu qua `preprocess.py` và đưa qua 4 mô hình Machine Learning (`Random Forest`, `Decision Tree`, `Gradient Boosting`, `SVM`) để đưa ra kết quả phán đoán:

```text
================================================================
PACKAGE: requests
================================================================
Model                Prediction      Probability  
----------------------------------------------------------------
Random-Forest        BENIGN            2.14%                  
Decision-Tree        BENIGN            0.00%                  
Gradient-Boosting    BENIGN            0.85%                  
SVM                  BENIGN            3.20%          
================================================================
```
