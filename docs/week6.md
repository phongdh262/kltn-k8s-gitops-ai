# BÁO CÁO TIẾN ĐỘ TUẦN 6

- **Đề tài:** Xây dựng nền tảng GitOps trên Kubernetes tích hợp AI Agent hỗ trợ vận hành
- **Sinh viên thực hiện:** Đinh Hồng Phong - 24TX810013
- **Thời gian báo cáo:** Tuần 6
- **Repository:** [phongdh262/kltn-k8s-gitops-ai](https://github.com/phongdh262/kltn-k8s-gitops-ai)
- **Commit Tuần 6:** [64a584f](https://github.com/phongdh262/kltn-k8s-gitops-ai/commit/64a584f)

---

## 1. Kết quả Tuần 5
- Thiết lập phân quyền Kubernetes RBAC đặc quyền tối thiểu (`ClusterRole` chỉ đọc không truy cập `secrets`, `Role` cục bộ theo namespace) trên VPS 01.
- Đóng gói và triển khai Pod `chatops-agent` (`uv` multi-stage, `non-root` UID `10001`) trên VPS 02 (`k3s-worker-01`), tích hợp AI Gateway đa tầng (`gemini-flash-lite-latest` kết hợp dự phòng `openai/gpt-oss-20b` trên Groq).
- Hoàn thành kiểm thử lệnh tra cứu nhanh, chẩn đoán RCA từ crash log, chặn lệnh cấm qua `Zero-Trust Policy Gate` và kiểm thử tải `k6` (10.790 requests, 30 VUs) đối chiếu trên Grafana Dashboard.
- Chi tiết báo cáo tuần 5: [docs/week5.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/docs/week5.md)

---

## 2. Công việc đã thực hiện trong Tuần 6

### 2.1. Triển khai Internal Webhook Service & Chính sách Mạng `NetworkPolicy`
- Bổ sung module `webhooks.py` (FastAPI lắng nghe cổng `8000/TCP`) và `watcher.py` trong mã nguồn AI ChatOps Agent tại `Ha_tang/cau_hinh/06_AI_ChatOps/agent_src/`.
- Triển khai Service `01-webhook-service.yaml` (`ClusterIP: 8000`) và `02-networkpolicy.yaml` trong namespace `operations`, chỉ cho phép Pod từ namespace `monitoring` và `argocd` kết nối vào cổng `8000/TCP`, chặn toàn bộ kết nối từ các namespace khác.

### 2.2. Tích hợp Cảnh báo Chủ động Grafana & Argo CD qua WireGuard (Phân biệt Sự kiện & Chống Gửi Trùng)
- Cấu hình **Grafana Unified Alerting** trên VPS 03 (`k3s-worker-02`) đẩy cảnh báo vượt ngưỡng chỉ số tài nguyên (PromQL) qua đường hầm `wg0` vào endpoint `/webhooks/grafana` (`[METRIC ALERT - GRAFANA]`).
- Cấu hình **Argo CD Notifications** trên VPS 02 (`k3s-worker-01`) bắt các sự kiện sai lệch đồng bộ cấu hình GitOps (`on-sync-failed`, `on-out-of-sync`) gửi vào endpoint `/webhooks/argocd` (`[GITOPS EVENT - ARGO CD]`), tách biệt với cảnh báo tài nguyên của Grafana và sự cố container của Watcher.
- Xây dựng hàm khử trùng sự kiện `should_suppress_duplicate` theo khóa `fingerprint` với cửa sổ thời gian 90 giây để ngăn chặn gửi lặp thông báo.

### 2.3. Kích hoạt `Proactive K8s Watcher` Phát hiện Sự cố Dưới 5 Giây
- Kích hoạt vòng lặp giám sát chủ động `run_proactive_k8s_watcher` (chu kỳ 5 giây) theo dõi trạng thái `Ready` của 3 VPS Node và số lần `Restarts` / `Waiting` lỗi của Pod trong namespace `demo-app`.
- Khi phát hiện sự cố container crash hoặc Node `NotReady`, hệ thống thu thập `[PREVIOUS CRASH LOG]`, K8s Events, chỉ số PromQL và gửi báo cáo phân tích RCA (`[REALTIME WATCHER - K8S]`) về Telegram.

---

## 3. Minh chứng kết quả trên GitHub

- **Báo cáo Tuần 6:** [docs/week6.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/docs/week6.md)
- **Thư mục cấu hình & tài liệu Tuần 6:** [Ha_tang/cau_hinh/07_EventDriven_Alerting_NetPol/](https://github.com/phongdh262/kltn-k8s-gitops-ai/tree/main/Ha_tang/cau_hinh/07_EventDriven_Alerting_NetPol)
- **Mã nguồn Agent cập nhật (`webhooks.py`, `watcher.py`):** [Ha_tang/cau_hinh/06_AI_ChatOps/agent_src/app/](https://github.com/phongdh262/kltn-k8s-gitops-ai/tree/main/Ha_tang/cau_hinh/06_AI_ChatOps/agent_src/app)

### 3.1. Thiết lập `NetworkPolicy` & Internal Webhook trên VPS 01:
- Tài liệu cấu hình: [Ha_tang/cau_hinh/07_EventDriven_Alerting_NetPol/vps01_netpol_watcher_setup.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/07_EventDriven_Alerting_NetPol/vps01_netpol_watcher_setup.md)
- Manifest Service & NetworkPolicy:
  - [01-webhook-service.yaml](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/07_EventDriven_Alerting_NetPol/manifests/01-webhook-service.yaml)
  - [02-networkpolicy.yaml](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/07_EventDriven_Alerting_NetPol/manifests/02-networkpolicy.yaml)
- Ảnh minh chứng:
  - Kiểm chứng `NetworkPolicy` cho phép `monitoring` và chặn `demo-app`: [`netpol-operations-verify.png`](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/07_EventDriven_Alerting_NetPol/images/netpol-operations-verify.png)

### 3.2. Kết nối Cảnh báo Grafana Unified Alerting (VPS 03) & Argo CD Notifications (VPS 02):
- Tài liệu cấu hình Grafana Alerting: [Ha_tang/cau_hinh/07_EventDriven_Alerting_NetPol/vps03_grafana_alerting_setup.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/07_EventDriven_Alerting_NetPol/vps03_grafana_alerting_setup.md)
- Tài liệu cấu hình Argo CD Notifications: [Ha_tang/cau_hinh/07_EventDriven_Alerting_NetPol/vps02_argocd_notifications_setup.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/07_EventDriven_Alerting_NetPol/vps02_argocd_notifications_setup.md)
- File cấu hình:
  - [grafana-contactpoint-values.yaml](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/07_EventDriven_Alerting_NetPol/configs/grafana-contactpoint-values.yaml)
  - [argocd-notifications-cm.yaml](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/07_EventDriven_Alerting_NetPol/configs/argocd-notifications-cm.yaml)
- Ảnh minh chứng:
  - Cảnh báo chỉ số tài nguyên từ Grafana qua WireGuard: [`grafana-webhook-alert.png`](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/07_EventDriven_Alerting_NetPol/images/grafana-webhook-alert.png)
  - Thông báo sự kiện đồng bộ GitOps từ Argo CD: [`argocd-webhook-event.png`](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/07_EventDriven_Alerting_NetPol/images/argocd-webhook-event.png)

### 3.3. Kiểm thử `Proactive K8s Watcher` (`< 5s` MTTD):
- Tài liệu kiểm thử tổng hợp: [Ha_tang/cau_hinh/07_EventDriven_Alerting_NetPol/00_kiem_tra_canh_bao_chu_dong.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/07_EventDriven_Alerting_NetPol/00_kiem_tra_canh_bao_chu_dong.md)
- Ảnh minh chứng:
  - Phát hiện sự cố Pod crash tự động dưới 5 giây kèm chẩn đoán RCA: [`proactive-watcher-rca.png`](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/07_EventDriven_Alerting_NetPol/images/proactive-watcher-rca.png)

---

## 4. Khai báo sử dụng AI
- **Tên công cụ & Phiên bản:** Google Gemini, model 3.8 flash
- **Mục đích:** Hỗ trợ viết module tiếp nhận Webhook (`webhooks.py`), vòng lặp giám sát sự cố (`watcher.py`), manifest `NetworkPolicy` và cấu hình Contact Point cho Grafana / Argo CD.
- **Phần AI hỗ trợ/tạo ra:**
  - Module `webhooks.py`, `watcher.py` và các file cấu hình `01-webhook-service.yaml`, `02-networkpolicy.yaml`, `grafana-contactpoint-values.yaml`, `argocd-notifications-cm.yaml`.
- **Phần sinh viên tự thực hiện và kiểm chứng:**
  - Cấu hình lại container image trên VPS 02, áp dụng `NetworkPolicy` trên VPS 01 và kiểm tra kết nối thực tế giữa các namespace.
  - Cấu hình Helm upgrade cho Grafana trên VPS 03, thiết lập Argo CD Notifications trên VPS 02 và giả lập sự cố kiểm chứng thời gian phát hiện `< 5s`.

---

## 5. Kế hoạch Tuần 7
1. Triển khai cơ chế phê duyệt **Human-in-the-Loop (HITL)** qua nút bấm Inline trên Telegram kết hợp GitHub API để thực thi thao tác chuẩn GitOps (`Scale Replicas`, `Rollout Restart`, `Argo CD Hard Refresh`) và ghi nhật ký kiểm toán (`/audit`).
2. Xây dựng bộ kiểm thử tự động `Pytest` và thiết lập pipeline **GitHub Actions CI/CD** tự động kiểm tra mã nguồn, đóng gói image `chatops-agent` lên `ghcr.io` và đăng ký Argo CD Application tự quản lý vòng đời Agent.