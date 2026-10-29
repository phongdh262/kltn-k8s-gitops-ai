# BÁO CÁO TIẾN ĐỘ TUẦN 4

- **Đề tài:** Xây dựng nền tảng GitOps trên Kubernetes tích hợp AI Agent hỗ trợ vận hành
- **Sinh viên thực hiện:** Đinh Hồng Phong - 24TX810013
- **Thời gian báo cáo:** Tuần 4
- **Repository:** [phongdh262/kltn-k8s-gitops-ai](https://github.com/phongdh262/kltn-k8s-gitops-ai)
- **Commit Tuần 4:** [bf42672](https://github.com/phongdh262/kltn-k8s-gitops-ai/commit/bf42672) 

---

## 1. Kết quả Tuần 3
- Khởi tạo thành công cụm K3s Cluster 3-node trên nền mạng riêng ảo WireGuard Full Mesh (`10.10.0.1`, `10.10.0.2`, `10.10.0.3`):
  - **VPS 01 (`k3s-master`)**: Control Plane, Ingress Controller (Traefik), Local Path StorageClass.
  - **VPS 02 (`k3s-worker-01`)**: K3s Agent, gán nhãn `workload=operations-argocd`.
  - **VPS 03 (`k3s-worker-02`)**: K3s Agent, gán nhãn `workload=monitoring`.
- Giao tiếp nội bộ giữa Master, Agent và mạng Pod-to-Pod thông suốt qua giao diện mạng `wg0`.
- Kiểm thử Ingress Traefik trên Master thành công với ứng dụng kiểm thử `test-ingress.yaml`.
- Chi tiết báo cáo tuần 3: [docs/week3.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/docs/week3.md)

---

## 2. Công việc đã thực hiện trong Tuần 4

### 2.1. Cài đặt GitOps Argo CD trên VPS 02 (`k3s-worker-01`)
- Tạo namespace `argocd` trên cụm.
- Triển khai Argo CD manifest chính thức của Argo Project.
- Áp dụng cấu hình phân vùng tài nguyên: Ghim toàn bộ các Pod của Argo CD (`argocd-server`, `argocd-repo-server`, `argocd-dex-server`, `argocd-redis`, `argocd-notifications-controller`, `argocd-application-controller`) chạy cố định trên node `k3s-worker-01` qua `nodeSelector: workload=operations-argocd`.
- Cấu hình chế độ insecure (`server.insecure: "true"`) cho Argo CD Server thông qua ConfigMap `argocd-cmd-params-cm` để giao tiếp HTTP nội bộ với Traefik Ingress.
- Xác nhận trạng thái `Running (1/1 Ready)` toàn bộ Pod trong namespace `argocd` trên node Worker 1.

### 2.2. Cấu hình Ingress Traefik.
- Xây dựng manifest Ingress Traefik `argocd-ingress.yaml` tại VPS 01 (Master) với router entrypoints `web,websecure`.
- Khai báo routing rule với host `argocd.phongdinh.info.vn` chuyển tiếp về service `argocd-server:80`.
- Tích hợp `cert-manager` và `ClusterIssuer` (Let's Encrypt Production).

### 2.3. Khởi tạo tài khoản quản trị và bảo mật Argo CD
- Trích xuất mật khẩu ban đầu từ Secret `argocd-initial-admin-secret` bằng lệnh giải mã Base64.
- Đăng nhập giao diện Web UI, xác nhận tính năng quản trị cluster và tiếp nhận repository.

### 2.4. Thiết lập GitOps và cấu hình ứng dụng.
- Xây dựng file manifest Kubernetes mẫu `sample-app.yaml`:
  - 02 replica của Web App trên 2 Worker qua chính sách `podAntiAffinity` mềm (`preferredDuringSchedulingIgnoredDuringExecution`).
  - Khai báo độc lập `readinessProbe` và `livenessProbe` để kiểm soát lưu lượng và tính tự phục hồi khi xảy ra sự cố.
  - Chuẩn bị sẵn biến môi trường kết nối database PostgreSQL nội bộ cụm qua mạng WireGuard.
- Xây dựng manifest Application CRD `application-web-app.yaml` kết nối repository GitOps với chính sách tự động đồng bộ (`automated: {prune: true, selfHeal: true}`).
- Định tuyến Ingress Traefik cho host `app.phongdinh.info.vn` tích hợp chứng chỉ SSL HTTPS qua `cert-manager`.
- Truy cập thành công `https://app.phongdinh.info.vn` từ trình duyệt và kiểm tra cơ chế cân bằng tải giữa 2 Pod trên Worker 1 và Worker 2.

### 2.5. Triển khai cơ sở dữ liệu PostgreSQL trên VPS 01 (Master)
- Xây dựng manifest `postgres-deployment.yaml`: Chạy trên node `k3s-master` qua `nodeSelector: kubernetes.io/hostname: k3s-master`.
- Cấp phát PersistentVolumeClaim `postgres-pvc` dung lượng 5Gi thông qua StorageClass mặc định `local-path`.
- Tạo Secret lưu trữ mật khẩu cơ sở dữ liệu an toàn và Service `postgres-service:5432` nội bộ trong namespace `database`.
- Xác nhận Pod PostgreSQL hoạt động ổn định (`1/1 Ready`), PVC chuyển trạng thái `Bound`, sẵn sàng cho ứng dụng Web lưu trữ dữ liệu qua kết nối mạng WireGuard.

### 2.6. Triển khai giám sát Prometheus & Grafana trên VPS 03 (Worker 2)
- Cài đặt `kube-prometheus-stack` qua Helm với file cấu hình tinh gọn `monitoring-values.yaml`:
  - Giới hạn thời gian lưu trữ metrics xuống 3 ngày (`retention: 3d`) và cấp phát 10Gi bộ nhớ đĩa cục bộ qua `local-path`.
  - Ghim toàn bộ Prometheus, Grafana và kube-state-metrics lên `k3s-worker-02` qua `nodeSelector: workload=monitoring`.
  - Giữ nguyên `nodeExporter` chạy dạng DaemonSet trên cả 3 VPS để đo đạc CPU/RAM.
- Xây dựng manifest Ingress Traefik `grafana-ingress.yaml` tại VPS 01 chuyển tiếp lưu lượng host `grafana.phongdinh.info.vn` vào Grafana Dashboard có bảo mật HTTPS.
- Xác nhận các Pod giám sát đều `Running` trên Worker 2 và truy cập thành công giao diện Grafana.

---

## 3. Minh chứng kết quả trên GitHub

- **Báo cáo Tuần 4:** [docs/week4.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/docs/week4.md)
- **Thư mục cấu hình Tuần 4:** [Ha_tang/cau_hinh/05_ArgoCD_GitOps/](https://github.com/phongdh262/kltn-k8s-gitops-ai/tree/main/Ha_tang/cau_hinh/05_ArgoCD_GitOps)

### 3.1. Cài đặt và cấu hình Argo CD trên VPS 02:
- Tài liệu cấu hình chi tiết: [Ha_tang/cau_hinh/05_ArgoCD_GitOps/vps02_argocd_setup.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/05_ArgoCD_GitOps/vps02_argocd_setup.md)
- Manifest Ingress Traefik: [Ha_tang/cau_hinh/05_ArgoCD_GitOps/configs/argocd-ingress.yaml](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/05_ArgoCD_GitOps/configs/argocd-ingress.yaml)
- Manifest ClusterIssuer Let's Encrypt: [Ha_tang/cau_hinh/05_ArgoCD_GitOps/configs/letsencrypt-issuer.yaml](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/05_ArgoCD_GitOps/configs/letsencrypt-issuer.yaml)
- Ảnh minh chứng:
  - Trạng thái các Pod Argo CD chạy trên Worker 1 (`kubectl get pods -n argocd -o wide`): [`argocd-pods-worker01.png`](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/05_ArgoCD_GitOps/images/argocd-pods-worker01.png)
  - Lấy chuỗi mật khẩu admin khởi tạo từ Secret: [`argocd-initial-admin-secret.png`](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/05_ArgoCD_GitOps/images/argocd-initial-admin-secret.png)
  - Kiểm tra trạng thái Ingress của Argo CD: [`argocd-ingress.png`](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/05_ArgoCD_GitOps/images/argocd-ingress.png)
  - Giao diện đăng nhập Argo CD Web UI: [`argo-cd.png`](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/05_ArgoCD_GitOps/images/argo-cd.png)
  - Giao diện Dashboard quản trị Web UI: [`argocd-dashboard.png`](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/05_ArgoCD_GitOps/images/argocd-dashboard.png)

### 3.2. Kiểm thử GitOps và Phân bổ Workload:
- Tài liệu kiểm thử vận hành: [Ha_tang/cau_hinh/05_ArgoCD_GitOps/00_kiem_tra_argocd_gitops.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/05_ArgoCD_GitOps/00_kiem_tra_argocd_gitops.md)
- Manifest ứng dụng mẫu 2 replica: [Ha_tang/cau_hinh/05_ArgoCD_GitOps/configs/sample-app.yaml](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/05_ArgoCD_GitOps/configs/sample-app.yaml)
- Manifest Application CRD: [Ha_tang/cau_hinh/05_ArgoCD_GitOps/configs/application-web-app.yaml](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/05_ArgoCD_GitOps/configs/application-web-app.yaml)
- Ảnh minh chứng:
  - Phân bổ 2 replica của Web App trên 2 Worker qua PodAntiAffinity: [`webapp-replicas-distribution.png`](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/05_ArgoCD_GitOps/images/webapp-replicas-distribution.png)
  - Trạng thái Synced và Healthy của Application trên Argo CD: [`argocd-app-synced-healthy.png`](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/05_ArgoCD_GitOps/images/argocd-app-synced-healthy.png)
  - Ingress HTTPS của ứng dụng Web: [`ingress-https-web.png`](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/05_ArgoCD_GitOps/images/ingress-https-web.png)
  - Truy cập Web App và kiểm chứng cân bằng tải: [`load-web.png`](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/05_ArgoCD_GitOps/images/load-web.png)

### 3.3. Cơ sở dữ liệu và Giám sát:
- Tài liệu cấu hình Master (PostgreSQL & Ingress): [Ha_tang/cau_hinh/05_ArgoCD_GitOps/vps01_master_database_ingress.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/05_ArgoCD_GitOps/vps01_master_database_ingress.md)
- Tài liệu cấu hình Worker 2 (Prometheus & Grafana): [Ha_tang/cau_hinh/05_ArgoCD_GitOps/vps03_monitoring_setup.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/05_ArgoCD_GitOps/vps03_monitoring_setup.md)
- Manifest cơ sở dữ liệu PostgreSQL: [Ha_tang/cau_hinh/05_ArgoCD_GitOps/configs/postgres-deployment.yaml](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/05_ArgoCD_GitOps/configs/postgres-deployment.yaml)
- File values cấu hình Helm cho Prometheus/Grafana: [Ha_tang/cau_hinh/05_ArgoCD_GitOps/configs/monitoring-values.yaml](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/05_ArgoCD_GitOps/configs/monitoring-values.yaml)
- Manifest Ingress Traefik cho Grafana: [Ha_tang/cau_hinh/05_ArgoCD_GitOps/configs/grafana-ingress.yaml](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/05_ArgoCD_GitOps/configs/grafana-ingress.yaml)
- Ảnh minh chứng:
  - Trạng thái Pod và PVC PostgreSQL trên Master: [`postgres-pod-pvc-master.png`](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/05_ArgoCD_GitOps/images/postgres-pod-pvc-master.png)
  - Ingress Traefik của Grafana trên Master: [`grafana-ingress.png`](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/05_ArgoCD_GitOps/images/grafana-ingress.png)
  - Trạng thái Pods Giám sát chạy trên Worker 2: [`monitoring-pods-worker02.png`](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/05_ArgoCD_GitOps/images/monitoring-pods-worker02.png)
  - Giao diện Dashboard Grafana Node Exporter: [`grafana-dashboard-node-exporter.png`](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/05_ArgoCD_GitOps/images/grafana-dashboard-node-exporter.png)

---

## 4. Khai báo sử dụng AI
- **Tên công cụ & Phiên bản:** Google Gemini 3.8 Flash
- **Mục đích:** Hỗ trợ chuẩn hóa cú pháp manifest Ingress Traefik cho Argo CD và Grafana, kịch bản lệnh patch `nodeSelector` JSON, mẫu khai báo Argo CD Application CRD, manifest PostgreSQL Stateful và tối ưu file `monitoring-values.yaml`.
- **Phần AI hỗ trợ/tạo ra:**
  - File manifest `argocd-ingress.yaml`, `sample-app.yaml`, `application-web-app.yaml`, `postgres-deployment.yaml`, `grafana-ingress.yaml` và `monitoring-values.yaml`.
  - Cú pháp patch cấu hình `server.insecure` trong ConfigMap `argocd-cmd-params-cm` và lệnh lặp patch `nodeSelector`.
- **Phần sinh viên tự thực hiện và kiểm chứng:**
  - Trực tiếp chạy lệnh triển khai Argo CD trên VPS 02, PostgreSQL trên Master và stack Prometheus/Grafana trên Worker 2.
  - Khởi tạo tài khoản, đổi mật khẩu và xác thực giao diện quản trị Argo CD Web UI và Grafana Dashboard.
  - Kiểm tra tính tương thích phân bổ replica ứng dụng Web trên 2 node worker và liên thông mạng nội bộ WireGuard.
  - Soạn thảo và hoàn thiện các tài liệu báo cáo và cấu hình vào thư mục `Ha_tang/cau_hinh/05_ArgoCD_GitOps/`.

---

## 5. Kế hoạch Tuần 5
1. Triển khai **AI ChatOps Agent** và Telegram Bot.
2. Thiết lập Kubernetes RBAC.
3. Kiểm thử tương tác vận hành thực tế qua Telegram: tra cứu trạng thái Pod, lấy log chẩn đoán lỗi, kiểm duyệt an toàn lệnh cấm.
4. Chuẩn bị kịch bản kiểm thử tải bằng công cụ **k6** và thiết lập dashboard đo đạc thời gian phục hồi trên Grafana.
