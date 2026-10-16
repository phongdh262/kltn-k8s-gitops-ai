# BÁO CÁO TIẾN ĐỘ TUẦN 1

- **Đề tài:** Xây dựng nền tảng GitOps trên Kubernetes tích hợp AI Agent hỗ trợ vận hành
- **Sinh viên thực hiện:** Đinh Hồng Phong - 24TX810013
- **Thời gian báo cáo:** Tuần 1
- **Repository:** [phongdh262/kltn-k8s-gitops-ai](https://github.com/phongdh262/kltn-k8s-gitops-ai)

---

## 1. Mục tiêu tuần 1
- Tìm hiểu tài liệu liên quan đến việc triển khai hệ thống Kubernetes trên hạ tầng tài nguyên hạn chế.
- So sánh, đánh giá và lựa chọn các công nghệ cốt lõi phù hợp với bài toán của đề tài: K3s, WireGuard VPN Mesh, GitOps (Argo CD), tường lửa CSF và hệ thống giám sát Prometheus/Grafana.
- Xây dựng kiến trúc và quy hoạch tài nguyên hạ tầng 3 VPS (1 Master, 2 Workers).

---

## 2. Công việc đã thực hiện trong Tuần 1

### 2.1. Tìm hiểu công nghệ

1. **Tổng quan kiến trúc:** Tìm hiểu khóa khăn khi triển khai K8s trên đa VPS độc lập (tài nguyên RAM, thiếu mạng LAN riêng, rủi ro bảo mật CI/CD, vận hành thủ công).
   - Tài liệu: [Cong_nghe/01_Tong_quan_kien_truc.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Cong_nghe/01_Tong_quan_kien_truc.md)
2. **K3s vs Kubernetes tiêu chuẩn vs Docker Swarm:** So sánh và chọn K3s vì tiết kiệm >60% RAM cho Control Plane, dùng SQLite nhúng tránh nghẽn I/O đĩa.
   - Tài liệu: [Cong_nghe/02_k3s_vs_kubernetes.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Cong_nghe/02_k3s_vs_kubernetes.md)
3. **Quy trình GitOps với Argo CD:** Phân tích mô hình Pull-based, tránh lộ secret `kubeconfig`, hỗ trợ tự động hoàn nguyên (`Auto-heal`) và rollback.
   - Tài liệu: [Cong_nghe/03_gitops_argocd.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Cong_nghe/03_gitops_argocd.md)
4. **Bảo mật máy chủ với CSF Firewall:** So sánh CSF + LFD với UFW, thiết lập cơ chế tự động chặn brute-force SSH và quét cổng.
   - Tài liệu: [Cong_nghe/04_csf_firewall.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Cong_nghe/04_csf_firewall.md)
5. **Mạng riêng ảo WireGuard Full Mesh:** Thiết kế giải pháp mạng ảo mã hóa mức Linux Kernel (`10.10.0.0/24`) bảo vệ traffic giữa các node và Pod.
   - Tài liệu: [Cong_nghe/05_wireguard_vpn_mesh.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Cong_nghe/05_wireguard_vpn_mesh.md)
6. **Hệ thống giám sát Prometheus & Grafana:** Tìm hiểu cơ chế giám gát để đo đạc thời gian phục hồi dịch vụ.
   - Tài liệu: [Cong_nghe/06_monitoring_prometheus_grafana.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Cong_nghe/06_monitoring_prometheus_grafana.md)

### 2.2. Quy hoạch hạ tầng và tài nguyên 3 VPS
- Xác định thông số tài nguyên VPS cần sử dụng: mỗi máy 4 vCPU / 8GB RAM / 50GB SSD.
- Dải IP mạng nội bộ WireGuard (`10.10.0.1`, `10.10.0.2`, `10.10.0.3`).
- Bảng quy hoạch: [Ha_tang/quy_hoach_vps.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/quy_hoach_vps.md)

### 2.3. Minh chứng trên GitHub
- **Báo cáo chi tiết Tuần 1:** [docs/week1.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/docs/week1.md)
- **Link Commit tài liệu Tuần 1:** [5e9a608](https://github.com/phongdh262/kltn-k8s-gitops-ai/commit/5e9a60850bf48f1a50e4eb840adee958713a38e8)
- **Thư mục tài liệu:** [Cong_nghe/](https://github.com/phongdh262/kltn-k8s-gitops-ai/tree/main/Cong_nghe)

---

## 3. Kế hoạch Tuần 2
1. Cài đặt 03 VPS độc lập với IP Public.
2. Cài đặt hệ điều hành Ubuntu 24.04 LTS, tắt Swap, nạp kernel modules (`overlay`, `br_netfilter`), bật `ip_forward`.
3. Cài đặt và cấu hình tường lửa CSF + LFD trên cả 3 node, mở port dịch vụ.
4. Thiết lập mạng riêng ảo WireGuard (`10.10.0.0/24`) và kiểm tra ping thông mạng 3 VPS.