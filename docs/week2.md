# BÁO CÁO TIẾN ĐỘ TUẦN 2

- **Đề tài:** Xây dựng nền tảng GitOps trên Kubernetes tích hợp AI Agent hỗ trợ vận hành
- **Sinh viên thực hiện:** Đinh Hồng Phong - 24TX810013
- **Thời gian báo cáo:** Tuần 2
- **Repository:** [phongdh262/kltn-k8s-gitops-ai](https://github.com/phongdh262/kltn-k8s-gitops-ai)
- **Commit Tuần 2:** [5e9a608](https://github.com/phongdh262/kltn-k8s-gitops-ai/commit/5e9a60850bf48f1a50e4eb840adee958713a38e8)

---

## 1. Kết quả Tuần 1
- Tìm hiểu công nghệ: K3s, GitOps (Argo CD), WireGuard VPN, CSF Firewall, Prometheus & Grafana tại thư mục `Cong_nghe/`.
- Quy hoạch thông số 3 VPS, dải mạng nội bộ `10.10.0.0/24`: [Ha_tang/quy_hoach_vps.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/quy_hoach_vps.md)
- Chi tiết báo cáo tuần 1: [docs/week1.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/docs/week1.md)

---

## 2. Công việc đã thực hiện trong Tuần 2

### 2.1. Cài đặt và chuẩn hóa hệ điều hành trên cả 3 VPS
- Cấu hình 03 VPS độc lập (Ubuntu 24.04 LTS, mỗi VPS: 4 vCPU / 8GB RAM / 50GB SSD):
  - **VPS 01 (Master):** Public IP `103.110.85.106` | Hostname: `k3s-master`
  - **VPS 02 (Worker 1):** Public IP `103.110.85.111` | Hostname: `k3s-worker-01`
  - **VPS 03 (Worker 2):** Public IP `103.110.85.145` | Hostname: `k3s-worker-02`
- Đổi hostname, cập nhật hệ điều hành và cài đặt các gói công cụ mạng bổ trợ.
- Tắt Swap (`swapoff -a` và chỉnh `/etc/fstab`).
- Nạp Kernel Modules (`overlay`, `br_netfilter`) và kích hoạt `net.ipv4.ip_forward = 1` trong sysctl.
- Đồng bộ thời gian múi giờ Việt Nam (`Asia/Ho_Chi_Minh`) và kích hoạt NTP.

### 2.2. Triển khai tường lửa CSF & LFD
- Gỡ bỏ hoàn toàn `ufw` để tránh xung đột.
- Cài đặt CSF và LFD trên cả 3 VPS.
- Cấu hình mở port:
  - **VPS 01:** Mở TCP 80, 443 (HTTP/HTTPS Ingress) và UDP 51820 (WireGuard).
  - **VPS 02 & VPS 03:** Mở UDP 51820 (WireGuard). Không mở cổng dịch vụ nội bộ (K3s, ArgoCD, Prometheus) ra Internet.
- Cấu hình `ETH_DEVICE_SKIP = "wg0"` và thêm `10.10.0.0/24` vào `csf.allow`, cho phép toàn bộ lưu lượng Kubernetes lưu thông tự do trong mạng ảo.

### 2.3. Thiết lập mạng riêng ảo WireGuard Full Mesh
- Cài đặt `wireguard-tools` và tạo cặp khóa (Public/Private Key) riêng trên từng node.
- Cấu hình file `wg0.conf` kết nối Full Mesh Point-to-Point giữa 3 máy chủ:
  - VPS 01: `10.10.0.1/24`
  - VPS 02: `10.10.0.2/24`
  - VPS 03: `10.10.0.3/24`
- Cấu hình `PersistentKeepalive = 25` giây để giữ kết nối ổn định xuyên firewall/NAT.
- Khởi động service `wg-quick@wg0` và kiểm tra ping chéo thành công giữa 3 VPS.

---

## 3. Minh chứng kết quả trên GitHub

- **Báo cáo Tuần 2:** [docs/week2.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/docs/week2.md)
- **Link Commit Tuần 2:** [5e9a608](https://github.com/phongdh262/kltn-k8s-gitops-ai/commit/5e9a60850bf48f1a50e4eb840adee958713a38e8)
- **Bảng quy hoạch VPS:** [Ha_tang/quy_hoach_vps.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/quy_hoach_vps.md)

### 3.1. Cài đặt OS & Tắt Swap:
- **VPS 01 (Master):** [Ha_tang/cau_hinh/01_OS/vps01_k3s_master.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/01_OS/vps01_k3s_master.md) (Ảnh hostname: `image.png`, Ảnh Swap = 0B: `image-1.png`, Ảnh sysctl: `image-2.png`)
- **VPS 02 (Worker 1):** [Ha_tang/cau_hinh/01_OS/vps02_k3s_worker01.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/01_OS/vps02_k3s_worker01.md) (Ảnh hostname: `image-3.png`, Ảnh Swap: `image-4.png`, Ảnh sysctl: `image-5.png`)
- **VPS 03 (Worker 2):** [Ha_tang/cau_hinh/01_OS/vps03_k3s_worker02.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/01_OS/vps03_k3s_worker02.md) (Ảnh hostname: `image-6.png`, Ảnh Swap: `image-7.png`, Ảnh sysctl: `image-8.png`)

### 3.2. Cấu hình Firewall CSF:
- **VPS 01 (Master):** [Ha_tang/cau_hinh/02_Firewall_CSF/vps01_k3s_master.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/02_Firewall_CSF/vps01_k3s_master.md) (Ảnh trạng thái service: `image.png`, rules port mở: `image-1.png`)
- **VPS 02 (Worker 1):** [Ha_tang/cau_hinh/02_Firewall_CSF/vps02_k3s_worker01.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/02_Firewall_CSF/vps02_k3s_worker01.md) (Ảnh CSF status: `image-2.png`, `image-3.png`)
- **VPS 03 (Worker 2):** [Ha_tang/cau_hinh/02_Firewall_CSF/vps03_k3s_worker02.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/02_Firewall_CSF/vps03_k3s_worker02.md) (Ảnh CSF status: `image-4.png`, `image-5.png`)

### 3.3. Kết nối mạng ảo WireGuard Mesh & Ping:
- **VPS 01 (Master):** [Ha_tang/cau_hinh/03_Wireguard_VPN/vps01_k3s_master.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/03_Wireguard_VPN/vps01_k3s_master.md) (Ảnh `wg show`: `image-1.png`, Ảnh `ping` thông 10.10.0.2 và 10.10.0.3: `image.png`)
- **VPS 02 (Worker 1):** [Ha_tang/cau_hinh/03_Wireguard_VPN/vps02_k3s_worker01.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/03_Wireguard_VPN/vps02_k3s_worker01.md) (Ảnh `wg show`: `image-2.png`, Ảnh `ping`: `image-3.png`)
- **VPS 03 (Worker 2):** [Ha_tang/cau_hinh/03_Wireguard_VPN/vps03_k3s_worker02.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/03_Wireguard_VPN/vps03_k3s_worker02.md) (Ảnh `wg show`: `image-4.png`, Ảnh `ping`: `image-5.png`)

---

## 4. Khai báo sử dụng AI
- **Tên công cụ & Phiên bản:** Google Gemini 3.8 flash
- **Mục đích:** Hỗ trợ tìm kiếm tài liệu kỹ thuật, gợi ý cấu trúc báo cáo so sánh các giải pháp hạ tầng.
- **Phần AI hỗ trợ/tạo ra:**
  - Khung sườn dàn ý và nội dung lý thuyết tổng quan trong thư mục `Cong_nghe/`.
  - Mẫu cú pháp file cấu hình khởi tạo cho WireGuard (`wg0.conf`) và danh mục tham số kernel (`sysctl.conf`).
- **Phần sinh viên tự thực hiện và kiểm chứng:**
  - Trực tiếp cài đặt, cấu hình, kiểm tra trên 03 VPS.
  - Chụp ảnh màn hình và làm file tài liệu cấu hình tại thư mục `Ha_tang/cau_hinh/`.
- **Link minh chứng:**
  - Commit triển khai: [5e9a608](https://github.com/phongdh262/kltn-k8s-gitops-ai/commit/5e9a60850bf48f1a50e4eb840adee958713a38e8)
  - Thư mục cấu hình & ảnh thực tế: [Ha_tang/cau_hinh/](https://github.com/phongdh262/kltn-k8s-gitops-ai/tree/main/Ha_tang/cau_hinh)

---

## 5. Kế hoạch Tuần 3
1. Cài đặt cụm **K3s Server** trên VPS 01 (Master), cấu hình trên IP WireGuard `10.10.0.1`.
2. Cài đặt và kết nối 2 **K3s Agent** trên VPS 02 và VPS 03.
3. Kiểm tra hoạt động của cụm (`kubectl get nodes`), phân bổ NodeSelector / Labels cho các node.
4. Kiểm tra Traefik Ingress Controller và khả năng định tuyến.
