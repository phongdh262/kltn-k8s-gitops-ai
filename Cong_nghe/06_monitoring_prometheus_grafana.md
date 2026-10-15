# HỆ THỐNG GIÁM SÁT  PROMETHEUS VÀ GRAFANA

## 1. Tầm quan trọng của Observability trong cụm Kubernetes

Đối với một hệ thống phân tán đa máy chủ chạy container, việc theo dõi trạng thái sức khỏe không chỉ dừng lại ở mức "máy chủ còn bật hay tắt", mà cần đo lường liên tục.
- **Độ trễ (Latency):** Thời gian phản hồi của các request từ người dùng.
- **Lưu lượng (Traffic):** Số lượng request/giây mà hệ thống đang gánh chịu.
- **Tỉ lệ lỗi (Errors):** Số lượng request trả về mã lỗi HTTP 5xx.
- **Độ bão hòa (Saturation):** Tỉ lệ sử dụng CPU, RAM, Disk I/O trên từng node và từng container.

Việc thu thập chính xác các chỉ số là điều kiện để đánh giá thực nghiệm các kịch bản tự phục hồi (Self-healing), cân bằng tải và tính toán thời gian phục hồi dịch vụ.


## 2. Kiến trúc giải pháp giám sát

Hệ thống giám sát được bố trí tập trung trên **VPS 03 (k3s-worker-02)** để cô lập tải, tránh ảnh hưởng tài nguyên tới node Master và node chạy CI/CD (VPS 02):

```
                    ┌───────────────────────────────────────────────┐
                    │               VPS 03 (Worker 2)               │
                    │                                               │
                    │  ┌───────────────┐        ┌────────────────┐  │
                    │  │ Grafana UI    │ <───── │ Prometheus     │  │
                    │  │ (Dashboards)  │        │ (TSDB Engine)  │  │
                    │  └───────────────┘        └───────┬────────┘  │
                    └───────────────────────────────────┼───────────┘
                                                        │ (Kéo metric qua WireGuard: 10.10.0.x)
                         ┌──────────────────────────────┴──────────────────────────────┐
                         ▼                                                             ▼
        [Node Exporter - VPS 01]                                      [Node Exporter - VPS 02]
        [kube-state-metrics - K3s]                                    [cAdvisor - Kubelet]
```

## 3. Các thành phần chính trong hệ thống giám sát

1. **Prometheus Server:** Là Time-Series Database, định kỳ kéo metrics từ các endpoint theo chu kỳ scrape (15 giây) qua mạng nội bộ WireGuard.
2. **Node Exporter:** Chạy dưới dạng DaemonSet trên cả 3 VPS, thu thập số liệu phần cứng máy chủ (CPU, RAM, Disk IOPS, Network traffic).
3. **cAdvisor & kube-state-metrics:** Thu thập các thông số nội tại của Kubernetes (trạng thái Pod Running/Pending/Failed, số replica sẵn sàng, container resource limits & requests).
4. **Grafana:** Cung cấp giao diện trực quan hóa dữ liệu qua các biểu đồ thời gian, hỗ trợ xuất số liệu định lượng.


## 4. Tài liệu tham khảo
1. **Tài liệu chính thức Prometheus Documentation:** https://prometheus.io/docs/introduction/overview/
2. **Tài liệu chính thức Grafana Documentation:** https://grafana.com/docs/grafana/latest/
3. **Google SRE Book - Monitoring Distributed Systems (The 4 Golden Signals):** https://sre.google/sre-book/monitoring-distributed-systems/
4. **Mã nguồn Prometheus Operator (kube-prometheus-stack):** https://github.com/prometheus-operator/kube-prometheus
5. **Tài liệu kube-state-metrics:** https://github.com/kubernetes/kube-state-metrics

