# CẤU HÌNH GRAFANA UNIFIED ALERTING ĐẨY CẢNH BÁO QUA WIREGUARD

- **IP Public VPS 03**: `103.110.85.145`
- **Hostname**: `k3s-worker-02` (`workload=monitoring`)
- **IP WireGuard (`wg0`)**: `10.10.0.3/24`
- **Vai trò**: Sử dụng bộ cảnh báo nội tại của Grafana (`Grafana Unified Alerting`) đẩy cảnh báo vượt ngưỡng tài nguyên từ VPS 03 qua đường hầm `wg0` sang endpoint `/webhooks/grafana` của AI ChatOps Agent trên VPS 02.

---

## 1. Cập nhật Contact Point cho Grafana qua Helm

Thực hiện từ **VPS 01 (`k3s-master`)**:

```bash
set -euo pipefail
# 1. Đồng bộ khóa webhook từ Secret chatops-secrets sang Secret grafana-webhook-auth (namespace monitoring)
install -m 600 /dev/null grafana-webhook.secret.local.yaml
kubectl get secret chatops-secrets -n operations -o json | python3 -c '
import base64, json, sys
key = json.load(sys.stdin)["data"]["WEBHOOK_SECRET"]
value = base64.b64decode(key).decode().strip()
if not value or (value.startswith("<") and value.endswith(">")):
    sys.exit("WEBHOOK_SECRET thiếu hoặc còn placeholder")
json.dump({
    "apiVersion": "v1", "kind": "Secret", "type": "Opaque",
    "metadata": {"name": "grafana-webhook-auth", "namespace": "monitoring"},
    "data": {"WEBHOOK_SECRET": key}
}, sys.stdout)
' > grafana-webhook.secret.local.yaml
kubectl apply -f grafana-webhook.secret.local.yaml

# 2. Xác định phiên bản chart đang cài và nâng cấp kube-prometheus-stack nạp cấu hình Webhook
MONITORING_CHART_VERSION=$(helm list -n monitoring -o json | python3 -c '
import json, sys
release = next(r for r in json.load(sys.stdin) if r["name"] == "monitoring")
print(release["chart"].removeprefix("kube-prometheus-stack-"))
')

helm upgrade monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --version "$MONITORING_CHART_VERSION" \
  --reuse-values \
  -f Ha_tang/cau_hinh/05_ArgoCD_GitOps/configs/monitoring-values.yaml \
  -f Ha_tang/cau_hinh/07_EventDriven_Alerting_NetPol/configs/grafana-contactpoint-values.yaml \
  --set grafana.adminPassword=null

# 3. Khởi động lại Pod Grafana để nạp cấu hình và kiểm tra trạng thái
kubectl rollout restart deploy/monitoring-grafana -n monitoring
kubectl get pods -n monitoring -l app.kubernetes.io/name=grafana -o wide
```

### Thông số kỹ thuật kết nối:
- **Endpoint đích**: `http://chatops-agent.operations.svc.cluster.local:8000/webhooks/grafana`
- **Cơ chế xác thực**: `Authorization: Bearer <WEBHOOK_SECRET>`
- **Nhóm cảnh báo (`group_by`)**: `["alertname", "namespace"]`, thời gian gom nhóm `group_wait: 10s`, chu kỳ lặp `repeat_interval: 30m`.

---

## 2. Kiểm tra Contact Point trên Giao diện Grafana

1. Truy cập `https://grafana.phongdinh.info.vn` $\rightarrow$ **Alerting** $\rightarrow$ **Notification configuration** $\rightarrow$ **Contact points**.
2. Tại mục **`ai-chatops-webhook`**, chọn **View** $\rightarrow$ **Test** $\rightarrow$ **Send test notification** để kiểm tra kết nối từ VPS 03 (`monitoring`) sang VPS 02 (`operations`) qua giao diện `wg0`.

![Kiểm thử Contact Point từ Grafana sang AI ChatOps Agent](images/grafana-webhook-alert.png)
