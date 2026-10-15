# BÁO CÁO TIẾN ĐỘ TUẦN 2

- **Đề tài:** Xây dựng nền tảng GitOps trên Kubernetes tích hợp AI Agent hỗ trợ vận hành
- **Sinh viên thực hiện:** Đinh Hồng Phong - 24TX810013
- **Thời gian báo cáo:** Tuần 2
- **Repository:** [phongdh262/kltn-k8s-gitops-ai](https://github.com/phongdh262/kltn-k8s-gitops-ai)


## 1. Công việc đã thực hiện trong Tuần 2

### 1.1. Cài đặt hệ điều hành trên cả 3 VPS
- Tạo 03 VPS độc lập (Ubuntu 24.04 LTS, mỗi VPS: 4 vCPU / 8GB RAM / 50GB SSD):
  - **VPS 01 (Master):** Public IP `103.110.85.106` | Hostname: `k3s-master`
  - **VPS 02 (Worker 1):** Public IP `103.110.85.111` | Hostname: `k3s-worker-01`
  - **VPS 03 (Worker 2):** Public IP `103.110.85.145` | Hostname: `k3s-worker-02`
- Đổi hostname, cập nhật hệ điều hành và cài đặt các gói công cụ bổ trợ.
- Tắt Swap để K3s quản lý bộ nhớ và eviction.
- Nạp Kernel Modules (`overlay`, `br_netfilter`) và kích hoạt `net.ipv4.ip_forward = 1` trong sysctl.
- Đồng bộ thời gian múi giờ Việt Nam và kích hoạt NTP.

### 1.2. Triển khai tường lửa CSF & LFD
- Gỡ bỏ `ufw` để tránh xung đột.
- Cài đặt CSF (ConfigServer Security & Firewall) và LFD (Login Failure Daemon) trên cả 3 VPS.
- Cấu hình mở port:
  - **VPS 01:** Mở TCP 80, 443 (HTTP/HTTPS Ingress) và UDP 51820 (WireGuard).
  - **VPS 02 & VPS 03:** Mở UDP 51820 (WireGuard). Không mở cổng dịch vụ nội bộ (K3s, ArgoCD, Prometheus).
- Cấu hình `ETH_DEVICE_SKIP = "wg0"` và thêm `10.10.0.0/24` vào `csf.allow`, cho phép toàn bộ lưu lượng Kubernetes lưu thông tự do trong mạng ảo.

### 1.3. Thiết lập mạng riêng ảo WireGuard
- Cài đặt `wireguard-tools` và tạo cặp khóa (Public/Private Key) trên từng node.
- Cấu hình file `wg0.conf` kết nối Full Mesh Point-to-Point giữa 3 máy chủ:
  - VPS 01: `10.10.0.1/24`
  - VPS 02: `10.10.0.2/24`
  - VPS 03: `10.10.0.3/24`
- Cấu hình `PersistentKeepalive = 25` để giữ kết nối ổn định firewall/NAT.
- Khởi động service `wg-quick@wg0` và  kiểm tra ping chéo giữa 3 VPS.

---

## 2. Kết quả

### 2.1. Cài đặt OS & Tắt Swap:
- **VPS 01 (Master):** [Ha_tang/cau_hinh/01_OS/vps01_k3s_master.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/01_OS/vps01_k3s_master.md)
  - Ảnh kiểm tra hostname: `Ha_tang/cau_hinh/01_OS/image.png`
  - Ảnh kiểm tra Swap = 0B: `Ha_tang/cau_hinh/01_OS/image-1.png`
  - Ảnh kiểm tra kernel modules & sysctl: `Ha_tang/cau_hinh/01_OS/image-2.png`
- **VPS 02 (Worker 1):** [Ha_tang/cau_hinh/01_OS/vps02_k3s_worker01.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/01_OS/vps02_k3s_worker01.md)
  - Ảnh hostname: `Ha_tang/cau_hinh/01_OS/image-3.png` | Ảnh Swap: `Ha_tang/cau_hinh/01_OS/image-4.png` | Ảnh sysctl: `Ha_tang/cau_hinh/01_OS/image-5.png`
- **VPS 03 (Worker 2):** [Ha_tang/cau_hinh/01_OS/vps03_k3s_worker02.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/01_OS/vps03_k3s_worker02.md)
  - Ảnh hostname: `Ha_tang/cau_hinh/01_OS/image-6.png` | Ảnh Swap: `Ha_tang/cau_hinh/01_OS/image-7.png` | Ảnh sysctl: `Ha_tang/cau_hinh/01_OS/image-8.png`

### 2.2. Cấu hình Firewall CSF:
- **VPS 01 (Master):** [Ha_tang/cau_hinh/02_Firewall_CSF/vps01_k3s_master.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/02_Firewall_CSF/vps01_k3s_master.md) (Ảnh trạng thái service: `image.png`, rules port mở: `image-1.png`)
- **VPS 02 (Worker 1):** [Ha_tang/cau_hinh/02_Firewall_CSF/vps02_k3s_worker01.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/02_Firewall_CSF/vps02_k3s_worker01.md) (Ảnh CSF status: `image-2.png`, `image-3.png`)
- **VPS 03 (Worker 2):** [Ha_tang/cau_hinh/02_Firewall_CSF/vps03_k3s_worker02.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/02_Firewall_CSF/vps03_k3s_worker02.md) (Ảnh CSF status: `image-4.png`, `image-5.png`)

### 2.3. Kết nối mạng ảo WireGuard Mesh & Ping:
- **VPS 01 (Master):** [Ha_tang/cau_hinh/03_Wireguard_VPN/vps01_k3s_master.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/03_Wireguard_VPN/vps01_k3s_master.md)
  - Ảnh `wg show` kết nối 2 peer Worker 1 & 2: `Ha_tang/cau_hinh/03_Wireguard_VPN/image-1.png`
  - Ảnh `ping` thông 10.10.0.2 và 10.10.0.3 (0% packet loss): `Ha_tang/cau_hinh/03_Wireguard_VPN/image.png`
- **VPS 02 (Worker 1):** [Ha_tang/cau_hinh/03_Wireguard_VPN/vps02_k3s_worker01.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/03_Wireguard_VPN/vps02_k3s_worker01.md)
  - Ảnh `wg show`: `image-2.png` | Ảnh `ping` sang Master và Worker 2: `image-3.png`
- **VPS 03 (Worker 2):** [Ha_tang/cau_hinh/03_Wireguard_VPN/vps03_k3s_worker02.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/03_Wireguard_VPN/vps03_k3s_worker02.md)
  - Ảnh `wg show`: `image-4.png` | Ảnh `ping` sang Master và Worker 1: `image-5.png`

---

## 3. Khai báo sử dụng AI
- **Công cụ sử dụng:** Google Gemini Model
- **Mục đích hỗ trợ:**
  - Xây dựng tài liệu báo cáo so sánh các giải pháp hạ tầng.

## 5. Kế hoạch tuần 3
1. Cài đặt cụm **K3s Server** trên VPS 01 (Master).
2. Cài đặt 2 **K3s Agent** trên VPS 02 và VPS 03.
3. Kiểm tra hoạt động của cụm (`kubectl get nodes`), phân bổ NodeSelector / Labels cho các node.
4. Kiểm tra Traefik Ingress Controller và khả năng định tuyến.
