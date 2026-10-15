# HẠ TẦNG VÀ TÀI NGUYÊN 3 VPS

---

## 1. Thông số 3 VPS

| Tiêu chí | VPS 01 (Master) | VPS 02 (Worker 1) | VPS 03 (Worker 2) |
| :--- | :--- | :--- | :--- |
| **Hostname** | `k3s-master` | `k3s-worker-01` | `k3s-worker-02` |
| **Vai trò** | `control-plane, master` | `worker` | `worker` |
| **Cấu hình phần cứng** | 4 vCPU / 8 GB RAM / 50GB SSD | 4 vCPU / 8 GB RAM / 50GB SSD | 4 vCPU / 8 GB RAM / 50GB SSD |
| **Hệ điều hành** | Ubuntu 24.04 LTS | Ubuntu 24.04 LTS | Ubuntu 24.04 LTS |
| **Public IP** | `103.110.85.106` | `103.110.85.111` | `103.110.85.145` |
| **IP Mạng WireGuard (`wg0`)** | `10.10.0.1/24` | `10.10.0.2/24` | `10.10.0.3/24` |
| **TCSF Firewall** | Mở TCP 80, 443; UDP 51820 | Mở TCP 22; UDP 51820 | Mở TCP 22; UDP 51820 |
| **Phần mềm** | - K3s Server API<br>- Traefik Ingress<br>- PostgreSQL (Local PV)<br>- CSF + LFD Firewall | - K3s Agent<br>- Argo CD Controller/Server<br>- AI ChatOps Agent<br>- Web App Replica 1<br>- CSF + LFD Firewall | - K3s Agent<br>- Prometheus & Alertmanager<br>- Grafana Dashboards<br>- Web App Replica 2<br>- CSF + LFD Firewall |

---

## 2. Quy hoạch dải mạng (Network CIDR Allocation)

| Loại mạng | Dải địa chỉ IP (CIDR) | Giao diện mạng / Phạm vi | Mục đích sử dụng |
| :--- | :--- | :--- | :--- |
| **Overlay VPN (WireGuard)** | `10.10.0.0/24` | `wg0` trên 3 VPS | Kết nối mã hóa giữa các Node K3s |