# K3S, KUBERNETES, DOCKER SWARM

---

## 1. Tổng quan về K3s
Các giải pháp điều phối container trên môi trường tài nguyên giới hạn, K3s là một bản phân phối Kubernetes siêu nhẹ tương thích (Certified Kubernetes). K3s được thiết kế nhằm mục đích loại bỏ các thành phần cồng kềnh không thiết yếu của Kubernetes.

---

## 2. Bảng so sánh


| Tiêu chí so sánh | Kubernetes tiêu chuẩn (K8s/kubeadm) | Docker Swarm | K3s (Rancher) | Nhận xét |
| :--- | :--- | :--- | :--- | :--- |
| **Mức chiếm dụng RAM Control Plane** | Rất cao (~1.5 GB - 2.5 GB RAM) | Rất thấp (~150 - 250 MB) | **Thấp (~500 MB - 800 MB)** | K3s giúp tiết kiệm hơn 60% bộ nhớ RAM so với K8s tiêu chuẩn, giải phóng tài nguyên quý giá trên VPS Master cho Ingress và Database. |
| **Cơ chế lưu trữ trạng thái (State Store)** | Bắt buộc dùng `etcd` (đòi hỏi IOPS đĩa SSD rất lớn) | Dùng giao thức Raft nội bộ | Mặc định tích hợp **SQLite** (single server) hoặc etcd / Kine | K3s dùng SQLite nhúng, giảm nguy cơ nghẽn cổ chai I/O đĩa trên các dòng VPS giá rẻ. |
| **Độ tương thích chuẩn Kubernetes** | 100% chuẩn CNCF | Không tương thích (dùng Docker Compose spec riêng) | **100% chuẩn CNCF** | K3s hỗ trợ đầy đủ các tài nguyên tiêu chuẩn: Deployment, StatefulSet, Ingress, RBAC, CRD. |
| **Hỗ trợ công cụ Cloud Native (Argo CD, Prometheus)**| Tương thích | Hạn chế, không hỗ trợ hệ sinh thái Kubernetes Operator | **Tương thích** | Cho phép triển khai  các Operator phức tạp của Argo CD và kube-prometheus-stack. |
| **Thành phần tích hợp** | Không có (phải tự cài đặt CNI, Ingress Controller, CSI) | Tích hợp sẵn trong engine | Tích hợp sẵn Flannel CNI, Traefik Ingress, Local-path CSI | Giúp hệ thống tinh gọn, giảm thời gian cài đặt và cấu hình thủ công các phụ trợ. |
| **Độ phức tạp trong cài đặt và bảo trì** | Cao (nhiều tiến trình rời rạc, cấu hình chứng chỉ phức tạp) | Đơn giản | **Đơn giản** | Đơn giản quá trình khởi tạo, backup và nâng cấp cluster thông qua script tự động. |

---

## 3. Kết luận và Đề xuất áp dụng

- **Docker Swarm** nhẹ nhưng thiếu hệ sinh thái Cloud Native, không  đáp ứng các yêu cầu cốt lõi của đề tài
- **Kubernetes chuẩn** nặng nề, lãng phí tài nguyên VPS cho việc quản trị.
- **K3s là giải pháp tối ưu nhất**, đáp ứng tiêu chuẩn API của Kubernetes, tối ưu tài nguyên phần cứng cho hạ tầng 3 VPS của đề tài.

---

## 4. Tài liệu tham khảo

### 1. Tài liệu kỹ thuật chính thức:
- **K3s Architecture & Datastore Design:** https://docs.k3s.io/architecture
- **K3s Resource Requirements & Sizing:** https://docs.k3s.io/installation/requirements
- **Kubernetes Overview & Concepts:** https://kubernetes.io/docs/concepts/overview/
- **Docker Swarm Mode Overview:** https://docs.docker.com/engine/swarm/
- **Mã nguồn K3s trên GitHub (CNCF):** https://github.com/k3s-io/k3s

### 2. Bài viết:
- **Viblo - Triển khai Kubernetes Cluster với K3s:** https://viblo.asia/p/trien-khai-kubernetes-cluster-voi-k3s-tren-macos-MG24BPpBLz3
- **Viblo - Xây dựng cụm Kubernetes High Availability với K3s và K3d:** https://viblo.asia/p/xay-dung-cum-kubernetes-high-availability-voi-k3s-va-k3d-4P856ppRZY3
- **Viblo - Review một số giải pháp triển khai Kubernetes ở Local:** https://viblo.asia/p/kubernetes-review-mot-so-giai-phap-trien-khai-kubernetes-o-local-vyDZO6yQKwj
- **Viblo - Chuyên mục tổng hợp kiến thức K3s:** https://viblo.asia/tags/k3s
- **Viblo - Chuyên mục tổng hợp Docker Swarm:** https://viblo.asia/tags/docker-swarm



