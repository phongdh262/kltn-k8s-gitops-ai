# BÁO CÁO TIẾN ĐỘ TUẦN 5

- **Đề tài:** Xây dựng nền tảng GitOps trên Kubernetes tích hợp AI Agent hỗ trợ vận hành
- **Sinh viên thực hiện:** Đinh Hồng Phong - 24TX810013
- **Thời gian báo cáo:** Tuần 5
- **Repository:** [phongdh262/kltn-k8s-gitops-ai](https://github.com/phongdh262/kltn-k8s-gitops-ai)
- **Commit Tuần 5:** [42fb68e](https://github.com/phongdh262/kltn-k8s-gitops-ai/commit/42fb68e)

---

## 1. Kết quả Tuần 4
- Triển khai thành công **Argo CD GitOps** trên VPS 02 (`k3s-worker-01`, nhãn `workload=operations-argocd`), tích hợp chứng chỉ SSL Let's Encrypt qua Traefik Ingress (`https://argocd.phongdinh.info.vn`).
- Triển khai ứng dụng mẫu `web-app` (02 replica phân tách sang 2 Worker qua `podAntiAffinity` mềm) quản lý tự động bằng Argo CD (`automated: {prune: true, selfHeal: true}`) tại `https://app.phongdinh.info.vn`.
- Triển khai cơ sở dữ liệu **PostgreSQL** (`local-path` PVC 5Gi) trên VPS 01 (`k3s-master`) và ngăn xếp giám sát **Prometheus & Grafana** trên VPS 03 (`k3s-worker-02`) tại `https://grafana.phongdinh.info.vn`.
- Chi tiết báo cáo tuần 4: [docs/week4.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/docs/week4.md)

---

## 2. Công việc đã thực hiện trong Tuần 5

### 2.1. Thiết lập Phân quyền Kubernetes RBAC Phân tầng (Least Privilege) trên VPS 01
- Khởi tạo namespace `operations` và `ServiceAccount` `chatops-agent-sa` dành riêng cho AI ChatOps Agent.
- Xây dựng manifest phân quyền tối thiểu `01-namespace-rbac.yaml`:
  - `ClusterRole` `chatops-readonly-clusterrole`: Chỉ cấp quyền đọc (`get, list, watch`) trên `nodes`, `pods`, `pods/log`, `events`, `deployments` và `applications.argoproj.io`; **loại bỏ hoàn toàn quyền đọc `secrets`** và quyền `delete`/`exec`.
  - Cô lập quyền `patch` vào phạm vi hẹp thông qua `Role` cục bộ tại đúng namespace đích (`demo-app` và `argocd`), ngăn chặn Agent tác động sang `kube-system`, `database` hoặc `monitoring`.
- Kiểm chứng thực tế bằng bộ lệnh `kubectl auth can-i` xác nhận phân quyền hoạt động chính xác.

### 2.2. Xây dựng và Triển khai Lõi AI ChatOps Agent trên VPS 02 (`k3s-worker-01`)
- Xây dựng microservice Python bất đồng bộ (`asyncio`) tại `Ha_tang/cau_hinh/06_AI_ChatOps/agent_src/`:
  - Tích hợp **Telegram Async Long-Polling** (chiều ra HTTPS 443), tương thích hoàn toàn với chính sách tường lửa CSF đóng cổng Inbound trên VPS 02.
  - Kết nối đa nguồn dữ liệu nội bộ qua mạng mã hóa WireGuard (`wg0`): Kubernetes API, truy vấn PromQL trực tiếp tới Prometheus trên VPS 03 (`:9090`), đọc trạng thái đồng bộ Argo CD Application CRD và trích xuất thông minh cả log phiên container bị sập trước đó (`previous=True`).
  - Thiết kế **AI Gateway Đa tầng & Chịu lỗi**: Sử dụng **Google Gemini (`gemini-flash-lite-latest`)** kết hợp cơ chế tự động chuyển mạch dự phòng (**Auto-Failover**) sang **Groq (`openai/gpt-oss-20b`)**.
  - Trang bị lớp bảo vệ `Zero-Trust Policy Gate` chặn lệnh cấm tức thì (`< 1ms`) và bộ lọc `Secret/PII Redactor` che thông tin nhạy cảm trong log trước khi gửi lên Cloud LLM.
- Đóng gói **Multi-stage Docker Image với `uv`** chạy quyền `non-root` (`UID 10001`), `readOnlyRootFilesystem: true`, tiêu thụ bộ nhớ thấp (~60–80MB RAM); cấu hình `strategy: Recreate` và **Soft `nodeAffinity`** ưu tiên chạy trên VPS 02 (`k3s-worker-01`).

### 2.3. Kiểm thử Tương tác Vận hành trên Telegram & Chuẩn bị Kịch bản `k6`
- Kiểm thử nhóm lệnh tra cứu trực tiếp (`/status`, `/pods`, `/metrics`, `/gitops`, `/audit`) phản hồi `< 300ms` không phụ thuộc LLM.
- Kiểm thử tương tác ngôn ngữ tự nhiên Tiếng Việt đọc log chẩn đoán nguyên nhân sự cố (RCA) và kiểm chứng chặn các lệnh xóa hạ tầng, lệnh đọc Secret hoặc truy cập từ tài khoản lạ.
- Xây dựng kịch bản kiểm thử tải khởi tạo `k6-smoke-prepare.js` bắn thử lưu lượng HTTPS vào `https://app.phongdinh.info.vn` kết hợp đối chiếu trên Grafana Dashboard.

---

## 3. Minh chứng kết quả trên GitHub

- **Báo cáo Tuần 5:** [docs/week5.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/docs/week5.md)
- **Thư mục cấu hình & mã nguồn Tuần 5:** [Ha_tang/cau_hinh/06_AI_ChatOps/](https://github.com/phongdh262/kltn-k8s-gitops-ai/tree/main/Ha_tang/cau_hinh/06_AI_ChatOps)

### 3.1. Phân quyền RBAC Phân tầng trên Master (VPS 01):
- Tài liệu cấu hình: [Ha_tang/cau_hinh/06_AI_ChatOps/vps01_rbac_setup.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/06_AI_ChatOps/vps01_rbac_setup.md)
- Manifest RBAC: [Ha_tang/cau_hinh/06_AI_ChatOps/manifests/01-namespace-rbac.yaml](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/06_AI_ChatOps/manifests/01-namespace-rbac.yaml)
- Ảnh minh chứng:
  - Kiểm chứng quyền hạn tối thiểu với `kubectl auth can-i`: [`rbac-auth-can-i.png`](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/06_AI_ChatOps/images/rbac-auth-can-i.png)
  - Khởi tạo Kubernetes Secret lưu trữ API keys an toàn: [`chatops-secret-created.png`](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/06_AI_ChatOps/images/chatops-secret-created.png)

### 3.2. Đóng gói & Triển khai AI ChatOps Agent trên Worker 1 (VPS 02):
- Tài liệu triển khai: [Ha_tang/cau_hinh/06_AI_ChatOps/vps02_chatops_agent_setup.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/06_AI_ChatOps/vps02_chatops_agent_setup.md)
- Mã nguồn Agent & Dockerfile `uv`: [Ha_tang/cau_hinh/06_AI_ChatOps/agent_src/](https://github.com/phongdh262/kltn-k8s-gitops-ai/tree/main/Ha_tang/cau_hinh/06_AI_ChatOps/agent_src)
- Manifest Deployment Agent: [Ha_tang/cau_hinh/06_AI_ChatOps/manifests/02-chatops-deployment.yaml](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/06_AI_ChatOps/manifests/02-chatops-deployment.yaml)
- Ảnh minh chứng:
  - Pod `chatops-agent` hoạt động ổn định trên Worker 1: [`chatops-pod-worker01.png`](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/06_AI_ChatOps/images/chatops-pod-worker01.png)

### 3.3. Kiểm thử Vận hành Telegram, Chặn Lệnh Cấm & Chuẩn bị `k6`:
- Tài liệu kiểm thử: [Ha_tang/cau_hinh/06_AI_ChatOps/00_kiem_tra_chatops_rbac.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/06_AI_ChatOps/00_kiem_tra_chatops_rbac.md)
- Script `k6` chuẩn bị: [Ha_tang/cau_hinh/06_AI_ChatOps/configs/k6-smoke-prepare.js](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/06_AI_ChatOps/configs/k6-smoke-prepare.js)
- Ảnh minh chứng:
  - Tra cứu tức thời trạng thái 3 VPS & PromQL metrics qua Slash Commands: [`telegram-slash-commands.png`](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/06_AI_ChatOps/images/telegram-slash-commands.png)
  - Hỏi đáp đọc log phân tích nguyên nhân sự cố (RCA): [`telegram-rca-diagnosis.png`](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/06_AI_ChatOps/images/telegram-rca-diagnosis.png)
  - Kiểm duyệt chặn lệnh xóa hạ tầng và bảo vệ Secret: [`telegram-guardrail-block.png`](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/06_AI_ChatOps/images/telegram-guardrail-block.png)
  - Kiểm thử tải k6 trên Terminal (10.790 requests, 100% OK): [`k6-smoke-terminal.png`](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/06_AI_ChatOps/images/k6-smoke-terminal.png)
  - Biểu đồ băng thông mạng nhô đỉnh tải trên Grafana: [`k6-grafana-metrics.png`](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/06_AI_ChatOps/images/k6-grafana-metrics.png)

---

## 4. Khai báo sử dụng AI
- **Tên công cụ & Phiên bản:** Google Gemini, model 3.8 flash
- **Mục đích:** Hỗ trợ thiết kế kiến trúc microservice AI ChatOps Agent tối ưu tài nguyên, cấu hình RBAC đặc quyền tối thiểu, cơ chế lọc dữ liệu nhạy cảm và kịch bản khởi tạo `k6`.
- **Phần AI hỗ trợ/tạo ra:**
  - Bộ mã nguồn Python bất đồng bộ trong `Ha_tang/cau_hinh/06_AI_ChatOps/agent_src/`, `Dockerfile` multi-stage `uv`.
  - File manifest `01-namespace-rbac.yaml`, `02-chatops-deployment.yaml` và `k6-smoke-prepare.js`.
- **Phần sinh viên tự thực hiện và kiểm chứng:**
  - Khởi tạo Telegram Bot, thiết lập API Keys và triển khai Kubernetes Secret trên VPS 01.
  - Trực tiếp đóng gói container image trên VPS 02, triển khai Pod `chatops-agent` và chạy `kubectl auth can-i` kiểm chứng RBAC.
  - Thực hiện kiểm thử tương tác thực tế qua Telegram, kiểm tra chặn lệnh cấm, chạy thử `k6` và biên soạn tài liệu báo cáo Tuần 5.
  - **Phát hiện & khắc lỗi khi cấu hình AI:**
    1. *Lỗi Probe Timeout:* Lệnh kiểm tra `urllib.request` bị Kubelet ngắt do vượt timeout mặc định 1s; đã bổ sung `timeoutSeconds: 5` vào `readinessProbe`, `livenessProbe` giúp Pod chuyển trạng thái `1/1 Ready` ổn định.
    2. *Lỗi Group Privacy của Telegram:* Bot không phản hồi tin nhắn văn bản thường trong nhóm do cơ chế Privacy Mode; xử lý bằng cách cấp quyền quản trị cho Bot.
    3. *Lỗi Model Deprecation (404 Not Found & 503 High Demand):* Model `gemini-2.5-flash` cũ bị Google đóng đối với người dùng mới gây lỗi 404 và `gemini-3.8-flash` bị quá tải 503; xử lý bằng cách cấu hình chuyển sang `gemini-flash-lite-latest` kết hợp dự phòng `openai/gpt-oss-20b` trên Groq, tối ưu độ trễ phản hồi xuống chỉ còn 1.2s.

---

## 5. Kế hoạch Tuần 6
1. Thiết lập chính sách mạng nội bộ **`NetworkPolicy`** khóa cổng Webhook của AI ChatOps Agent.
2. Tích hợp luồng **Cảnh báo Chủ động (Event-Driven Proactive Alerting)** từ **Grafana Unified Alerting** (VPS 03) và **Argo CD Notifications** (VPS 02) qua đường hầm WireGuard (`wg0`) sang ChatOps Agent.
3. Kích hoạt **Proactive K8s Watcher** phát hiện sự cố sập Pod/Node theo thời gian thực (`< 5s`) và tự động gửi phân tích RCA về Telegram.
