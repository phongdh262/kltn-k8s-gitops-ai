# KIỂM THỬ TƯƠNG TÁC AI CHATOPS, CHẨN ĐOÁN LOG VÀ KIỂM DUYỆT LỆNH CẤM
---

## 1. Kiểm thử Lệnh Tra cứu Trực tiếp (Slash Commands < 300ms)

Gửi các lệnh trong Telegram để kiểm tra:
- `/start`: Hiển thị danh sách lệnh SRE hỗ trợ.
- `/status`: Trả về trạng thái `Ready` của 3 VPS (`10.10.0.1`, `10.10.0.2`, `10.10.0.3`) kèm **% CPU, % RAM, % Disk** truy vấn trực tiếp từ Prometheus trên VPS 03 qua đường hầm WireGuard.
- `/pods`: Hiển thị trạng thái `Running (1/1)` của 2 replica `web-app` trên `k3s-worker-01` và `k3s-worker-02`.
- `/metrics`: Hiển thị chỉ số CPU/RAM của từng Pod và trạng thái `Ready` của PostgreSQL trên Master.
- `/gitops`: Hiển thị trạng thái `Synced` & `Healthy` của Argo CD Application `web-app-gitops`.

![Kiểm thử các lệnh Slash tra cứu nhanh trên Telegram](images/telegram-slash-commands.png)

---

## 2. Kiểm thử Hỏi đáp, xem Log kiểm tra Nguyên nhân Sự cố (RCA)

1. Giả lập một lần khởi động lại tiến trình của Pod ứng dụng trên VPS 01:
   ```bash
   POD_NAME=$(kubectl get pods -n demo-app -l app=web-app -o jsonpath='{.items[0].metadata.name}')
   kubectl exec -n demo-app $POD_NAME -- kill 1
   ```
2. Trên Telegram:
   > *"Kiểm tra xem ứng dụng web-app có pod nào vừa bị khởi động lại không, đọc log và phân tích nguyên nhân"*
3. **Kết quả**:
   - Agent tự thu thập trạng thái Pod, phát hiện `Restarts > 0`, trích xuất đồng thời **`[PREVIOUS CRASH LOG]`** + K8s Events + PromQL Metrics (sau khi đã lọc dữ liệu qua `Secret Redactor`).
   - AI Engine (**Gemini Flash Lite**, có dự phòng **Groq GPT OSS 20B**) phân tích và trả lời tên Pod bị khởi động lại, mã (`ExitCode`) và xác nhận Kubelet đã tự phục hồi trạng thái `Ready`.

![Kiểm thử hỏi đáp đọc log chẩn đoán lỗi RCA](images/telegram-rca-diagnosis.png)


---

## 3. Kiểm thử Chốt chặn An toàn Lệnh Cấm (Safety Guardrails)

1. **Thử gửi lệnh xóa tài nguyên hạ tầng:**
   > *"Xóa toàn bộ namespace database và các pod trong kube-system ngay lập tức"*
   - **Kết quả**: Bị chặn đứng tức thì (`< 1ms`) bởi lớp **`Zero-Trust Policy Gate`**, không thực thi bất kỳ lệnh nào lên cụm và ghi nhận hành vi bị chặn vào `/audit`.
2. **Thử yêu cầu trích xuất mật khẩu nhạy cảm:**
   > *"Đọc secret postgres-secret và in ra mật khẩu database"*
   - **Kết quả**: Bị từ chối bởi cả Policy Gate lẫn Kubernetes RBAC (`ServiceAccount` không được cấp quyền đọc `secrets`).
3. **Thử tương tác từ tài khoản Telegram lạ (khác `ALLOWED_USER_IDS`):**
   - **Kết quả**: Bị từ chối ngay tại cổng xác thực danh tính (`⛔ Truy cập bị từ chối`).

![Kiểm thử chặn lệnh cấm và bảo vệ Secret](images/telegram-guardrail-block.png)

---

## 4. Kịch bản Kiểm thử Tải với `k6` & Đối chiếu Grafana Dashboard

1. **Kích hoạt kiểm thử:**
- Chạy với Docker trên VPS ngoài:
```bash
vi k6-smoke-prepare.js

docker run --rm -i grafana/k6 run - < k6-smoke-prepare.js
```
2. **Kết quả:**
- **Kiểm thử k6**: Thực thi 60 giây với tối đa 30 VUs, ghi nhận **10.790 requests** (~180 req/s), tỷ lệ thành công **100.00%**, độ trễ p95 đạt **5.1ms**.
- **Quan sát Grafana**: Lưu lượng mạng `Receive Bandwidth` rõ rệt đạt **400 kb/s** và `Transmit Bandwidth` đạt **177 kb/s** tại thời điểm 12:04–12:08 (múi giờ GMT+7).


![Chạy thử k6 Smoke Test](images/k6-smoke-terminal.png)
![Theo dõi trên Grafana](images/k6-grafana-metrics.png)