# BÁO CÁO TIẾN ĐỘ TUẦN 3

- **Đề tài:** Xây dựng nền tảng GitOps trên Kubernetes tích hợp AI Agent hỗ trợ vận hành
- **Sinh viên thực hiện:** Đinh Hồng Phong - 24TX810013
- **Thời gian báo cáo:** Tuần 3
- **Repository:** [phongdh262/kltn-k8s-gitops-ai](https://github.com/phongdh262/kltn-k8s-gitops-ai)
- **Commit Tuần 3:** [f99af6e](https://github.com/phongdh262/kltn-k8s-gitops-ai/commit/f99af6ebfd84364877edf7b0891db8acdffae285)

---

## 1. Kết quả Tuần 2
- Cấu hình 03 VPS độc lập (Ubuntu 24.04 LTS, mỗi VPS: 4 vCPU / 8GB RAM / 50GB SSD): đổi hostname, tắt Swap, nạp kernel modules (`overlay`, `br_netfilter`), cấu hình `net.ipv4.ip_forward = 1`.
- Cài đặt và cấu hình tường lửa CSF + LFD trên 3 VPS, cấu hình bỏ qua kiểm tra interface `wg0` (`ETH_DEVICE_SKIP = "wg0"`) và thêm subnet `10.10.0.0/24` vào `csf.allow`.
- Thiết lập mạng riêng ảo WireGuard Full Mesh (`10.10.0.1`, `10.10.0.2`, `10.10.0.3`), ping chéo giữa 3 VPS thông suốt.
- Chi tiết báo cáo tuần 2: [docs/week2.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/docs/week2.md)

---

## 2. Công việc đã thực hiện trong Tuần 3

### 2.1. Cài đặt và khởi tạo cụm K3s Server trên VPS 01 (Master)
- Cài đặt K3s Control Plane trên VPS 01 với cấu hình gắn trực tiếp vào card mạng WireGuard:
  - `--node-ip=10.10.0.1`: Bắt buộc K3s API server và Kubelet nhận diện IP nội bộ qua tunnel WireGuard.
  - `--advertise-address=10.10.0.1`: Địa chỉ IP API Server quảng bá cho các Worker Node kết nối qua WireGuard.
  - `--node-external-ip=103.110.85.106`: Gắn địa chỉ IP Public của VPS 01 để tiếp nhận traffic Ingress.
  - `--flannel-iface=wg0`: Cấu hình CNI Flannel truyền các gói tin mạng của Pod qua tunnel WireGuard đã được mã hóa.
  - `--tls-san=10.10.0.1` và `--tls-san=103.110.85.106`: Thêm IP nội bộ và IP Public vào chứng chỉ TLS API Server.
  - `--write-kubeconfig-mode=644`: Cấp quyền đọc file cấu hình `/etc/rancher/k3s/k3s.yaml`.
- Cấu hình bổ sung tường lửa CSF trên VPS 01: Thêm `cni+,flannel+` vào `ETH_DEVICE_SKIP = "wg0,cni+,flannel+"` trong `/etc/csf/csf.conf` để tránh việc tường lửa chặn nhầm gói tin mạng Pod của K3s.
- Lấy chuỗi `node-token` từ `/var/lib/rancher/k3s/server/node-token` trên VPS 01 để kết nối các Worker.
- Kiểm tra trạng thái dịch vụ `systemctl status k3s` hoạt động ổn định (`active (running)`). Thiết lập alias `k=kubectl` trên Master.

### 2.2. Kết nối các Worker Nodes (VPS 02 và VPS 03) vào K3s Cluster
- Cài đặt K3s Agent trên **VPS 02 (`k3s-worker-01`)**:
  - Trỏ biến môi trường `K3S_URL=https://10.10.0.1:6443` thông qua IP WireGuard an toàn của Master.
  - Thiết lập `--node-ip=10.10.0.2`, `--node-external-ip=103.110.85.111`, `--flannel-iface=wg0`.
  - Cấu hình tường lửa CSF: Thêm `ETH_DEVICE_SKIP = "wg0,cni+,flannel+"` trong `/etc/csf/csf.conf`.
  - Kích hoạt dịch vụ `k3s-agent` và xác nhận trạng thái `active (running)`.
- Cài đặt K3s Agent trên **VPS 03 (`k3s-worker-02`)**:
  - Trỏ biến môi trường `K3S_URL=https://10.10.0.1:6443` thông qua IP WireGuard an toàn của Master.
  - Thiết lập `--node-ip=10.10.0.3`, `--node-external-ip=103.110.85.145`, `--flannel-iface=wg0`.
  - Kích hoạt dịch vụ `k3s-agent` và xác nhận trạng thái `active (running)`.

### 2.3. Cấu hình Node Labels & Roles
- Kiểm tra danh sách node trên Master: cả 3 node (`k3s-master`, `k3s-worker-01`, `k3s-worker-02`) đều đạt trạng thái `Ready` với `INTERNAL-IP` lần lượt là `10.10.0.1`, `10.10.0.2`, `10.10.0.3` và `EXTERNAL-IP` là các IP Public tương ứng.
- Gán nhãn phân vùng vai trò (Workload Partitioning):
  - **Worker 01:**
    - `node-role.kubernetes.io/worker=worker-1`
    - `workload=operations-argocd` (GitOps Argo CD, AI ChatOps Agent và App Replica 1)
  - **Worker 02:**
    - `node-role.kubernetes.io/worker=worker-2`
    - `workload=monitoring` (Prometheus & Grafana và App Replica 2)

### 2.4. Kiểm tra thành phần hệ thống và mạng Pod-to-Pod
- Kiểm tra các Pod hệ thống trong namespace `kube-system`:
  - `coredns`: Dịch vụ phân giải tên miền nội bộ cụm hoạt động bình thường (`Running`).
  - `local-path-provisioner`: Bộ cấp phát Persistent Volume cục bộ mặc định (`(default)` StorageClass).
  - `traefik`: Ingress Controller sẵn sàng trên node `k3s-master`.
  - `svclb-traefik`: Bộ cân bằng tải dịch vụ (Klipper Service Load Balancer) sẵn sàng.
- Kiểm tra định tuyến Flannel Overlay trên interface `wg0`: Giao tiếp mạng Pod giữa các Node thông suốt qua kênh mã hóa WireGuard.
- Triển khai ứng dụng thử nghiệm (Test Ingress):
  - Triển khai manifest `test-ingress.yaml` chứa service `whoami` và Ingress route `/test`.
  - Kiểm tra truy cập HTTP qua `curl http://103.110.85.106/test` trả về thành công thông tin headers và IP của Pod xử lý.
  - Dọn dẹp tài nguyên kiểm thử sau khi xác nhận.

---

## 3. Minh chứng kết quả trên GitHub

- **Báo cáo Tuần 3:** [docs/week3.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/docs/week3.md)
- **Link Commit Tuần 3:** [f99af6e](https://github.com/phongdh262/kltn-k8s-gitops-ai/commit/f99af6ebfd84364877edf7b0891db8acdffae285)
- **Thư mục cấu hình K3s Cluster:** [Ha_tang/cau_hinh/04_K3s_Cluster/](https://github.com/phongdh262/kltn-k8s-gitops-ai/tree/main/Ha_tang/cau_hinh/04_K3s_Cluster)

### 3.1. Cài đặt K3s Master (VPS 01):
- Tài liệu cấu hình: [Ha_tang/cau_hinh/04_K3s_Cluster/vps01_k3s_master.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/04_K3s_Cluster/vps01_k3s_master.md)
- Ảnh:
  - Trạng thái dịch vụ K3s Server (`systemctl status k3s`): `image-4.png`
  - Node Master Ready và Internal IP `10.10.0.1` (`kubectl get nodes -o wide`): `image-8.png`
  - Lấy chuỗi Token kết nối cụm: `image-2.png`
  - Kiểm tra Pod hệ thống và StorageClass trên Master: `image-9.png`

### 3.2. Cài đặt K3s Agent Worker 1 (VPS 02):
- Tài liệu cấu hình: [Ha_tang/cau_hinh/04_K3s_Cluster/vps02_k3s_worker01.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/04_K3s_Cluster/vps02_k3s_worker01.md)
- Ảnh:
  - Trạng thái dịch vụ K3s Agent (`systemctl status k3s-agent`): `image-3.png`
  - Xác nhận gán nhãn vai trò và workload trên Worker 1 (`kubectl get nodes k3s-worker-01 --show-labels`): `image-5.png`

### 3.3. Cài đặt K3s Agent Worker 2 (VPS 03):
- Tài liệu cấu hình: [Ha_tang/cau_hinh/04_K3s_Cluster/vps03_k3s_worker02.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/04_K3s_Cluster/vps03_k3s_worker02.md)
- Ảnh:
  - Trạng thái dịch vụ K3s Agent (`systemctl status k3s-agent`): `image-6.png`
  - Xác nhận gán nhãn vai trò và workload trên Worker 2 (`kubectl get nodes k3s-worker-02 --show-labels`): `image-7.png`

### 3.4. Kiểm tra hoạt động toàn cụm K3s và Ingress:
- Tài liệu cấu hình chi tiết: [Ha_tang/cau_hinh/04_K3s_Cluster/00_kiem_tra_cum_k3s.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/04_K3s_Cluster/00_kiem_tra_cum_k3s.md)
- Minh chứng ảnh thực tế:
  - Danh sách 03 node Ready với đầy đủ Internal IP WireGuard và External IP (`kubectl get nodes -o wide`): `image-10.png`
  - Danh sách Pod hệ thống `kube-system` hoạt động: `image-9.png`
  - Kết quả kiểm tra Labels cho cả 3 node (`kubectl get nodes --show-labels`): `image-11.png`
  - Kiểm tra StorageClass mặc định `local-path` (`kubectl get storageclass`): `image-12.png`
  - Triển khai manifest Ingress kiểm thử và kiểm tra trạng thái Pods/Ingress: `image-13.png`
  - Kiểm thử định tuyến Ingress Traefik thành công qua `curl http://103.110.85.106/test`: `image-14.png`
  - Dọn dẹp tài nguyên kiểm thử: `image-15.png`

---

## 4. Khai báo sử dụng AI
- **Tên công cụ & Phiên bản:** Google Gemini 3.8 Flash
- **Mục đích:** Hỗ trợ phân tích, xử lý, tối ưu lệnh cấu hình và tạo file `test-ingress.yaml` để kiểm thử cụm.
- **Phần AI hỗ trợ/tạo ra:**
  - File manifest Kubernetes mẫu `test-ingress.yaml` để kiểm tra Ingress Traefik và phân bổ nhãn `nodeSelector`.
- **Phần sinh viên tự thực hiện và kiểm chứng:**
  - Trực tiếp chạy lệnh cài đặt, xử lý lỗi K3s Server trên VPS 01 và K3s Agent trên VPS 02, VPS 03.
  - Cấu hình phân bổ nhãn cho các node và kiểm tra tính liên lạc của Pod qua WireGuard.
  - Triển khai test Ingress và curl kiểm thử thực tế.
  - Chụp ảnh màn hình kết quả trên từng VPS và hoàn thành các file báo cáo và cấu hình vào thư mục `Ha_tang/cau_hinh/04_K3s_Cluster/`.

---

## 5. Kế hoạch Tuần 4
1. Triển khai **Argo CD** (GitOps Controller) trên VPS 02 (`k3s-worker-01`).
2. Cấu hình Ingress Traefik trên Master để mở giao diện quản trị Web UI cho Argo CD.
3. Thiết lập kho lưu trữ GitOps cho ứng dụng và kết nối Argo CD vào repository.
4. Chuẩn bị tài nguyên cài đặt cụm giám sát Prometheus/Grafana trên VPS 03.
