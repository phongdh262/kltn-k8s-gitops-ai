# BÁO CÁO TIẾN ĐỘ TUẦN 7

- **Đề tài:** Xây dựng nền tảng GitOps trên Kubernetes tích hợp AI Agent hỗ trợ vận hành
- **Sinh viên thực hiện:** Đinh Hồng Phong - 24TX810013
- **Thời gian báo cáo:** Tuần 7
- **Repository:** [phongdh262/kltn-k8s-gitops-ai](https://github.com/phongdh262/kltn-k8s-gitops-ai)
- **Commit Tuần 7:** [e26f29f](https://github.com/phongdh262/kltn-k8s-gitops-ai/commit/e26f29f)

---

## 1. Kết quả Tuần 6
- Triển khai AI ChatOps Agent `v1.1` mở cổng Webhook nội bộ `:8000/TCP`, giới hạn truy cập bằng `NetworkPolicy`.
- Tích hợp luồng cảnh báo chủ động qua mạng WireGuard (`wg0`) từ Grafana Unified Alerting (VPS 03), Argo CD Notifications (VPS 02) và `Proactive K8s Watcher`.
- Chi tiết báo cáo tuần 6: [docs/week6.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/docs/week6.md)

---

## 2. Công việc đã thực hiện trong Tuần 7

### 2.1. Triển khai Phê duyệt Thao tác Human-in-the-Loop (HITL) & GitOps Mutation (Agent `v1.2`)
- Cấu hình kiểm soát bảo mật cho quyền ghi HITL: tách Secret khỏi manifest Git, đặt quyền `kubeconfig` `600`, bắt buộc xác thực fail-closed (`ALLOWED_USER_IDS`, `WEBHOOK_SECRET`), lọc log nhạy cảm qua `redact_sensitive_text` / `RedactingFormatter` và truyền `GEMINI_API_KEY` qua header `x-goog-api-key`.
- Triển khai [05-hitl-scoped-roles.yaml](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/06_AI_ChatOps/manifests/05-hitl-scoped-roles.yaml) định nghĩa `Role` theo `resourceNames` (`["web-app"]` tại namespace `demo-app`, `["web-app-gitops"]` tại namespace `argocd`) và cấu hình `GITHUB_TOKEN` (Fine-grained PAT) cho kho GitOps.
- Xây dựng mô-đun phê duyệt `ActionGovernanceStore`:
  - Khởi tạo đề xuất dùng một lần (TTL `300s`) cho các tác vụ `SCALE_DEPLOYMENT`, `RESTART_DEPLOYMENT`, `SYNC_ARGOCD`; giới hạn tham số `replicas` trong khoảng `1..5` và gửi nút xác nhận `[Duyệt]` / `[Hủy bỏ]` trên Telegram.
  - Xác thực `user_id` thuộc `ALLOWED_USER_IDS` khi nhận callback, cập nhật `spec.replicas` trên GitHub bằng `ruamel.yaml` và gắn annotation `Hard Refresh` lên Argo CD Application.
  - Lưu nhật ký thao tác (`EXECUTED`, `REJECTED`, `CANCELLED`) qua lệnh `/audit`.

### 2.2. Xây dựng Bộ Kiểm thử Tự động (`Pytest`) & Pipeline GitHub Actions CI/CD
- Xây dựng 40 ca kiểm thử tự động tại [Ha_tang/cau_hinh/06_AI_ChatOps/agent_src/tests/](https://github.com/phongdh262/kltn-k8s-gitops-ai/tree/main/Ha_tang/cau_hinh/06_AI_ChatOps/agent_src/tests) (`test_config_security.py`, `test_webhooks.py`, `test_hitl.py`) với ngưỡng độ phủ `--cov-fail-under=75` trên `app.config`, `app.security`, `app.webhooks`.
- Thiết lập [.github/workflows/build-chatops-agent.yml](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/.github/workflows/build-chatops-agent.yml) gồm 6 giai đoạn:
  1. `ruff check app tests`
  2. `pytest -v --cov=app.config --cov=app.security --cov=app.webhooks --cov-report=term-missing --cov-fail-under=75`
  3. `pip-audit --desc on`
  4. `gitleaks/gitleaks-action@v2`
  5. Kiểm tra cú pháp YAML trong `Ha_tang/cau_hinh/06_AI_ChatOps/manifests/` và `Ha_tang/cau_hinh/07_EventDriven_Alerting_NetPol/manifests/`
  6. Đóng gói và đẩy container image (`non-root`, UID `10001`) lên `ghcr.io/phongdh262/kltn-chatops-agent` (tag `sha-<short_sha>`, `v1.2.0`, `latest`)
- Triển khai [application-chatops-agent.yaml](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/06_AI_ChatOps/configs/application-chatops-agent.yaml) đăng ký Application `chatops-agent-gitops` trên Argo CD (`selfHeal: true`, `prune: true`) cho namespace `operations`.

---

## 3. Minh chứng kết quả trên GitHub
- **Báo cáo Tuần 7:** [docs/week7.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/docs/week7.md)
- **Thư mục tài liệu triển khai Tuần 7:** [Ha_tang/cau_hinh/08_HITL_GitOps_CICD/](https://github.com/phongdh262/kltn-k8s-gitops-ai/tree/main/Ha_tang/cau_hinh/08_HITL_GitOps_CICD)
- **Mã nguồn Agent `v1.2` & Bộ kiểm thử `Pytest`:** [Ha_tang/cau_hinh/06_AI_ChatOps/agent_src/](https://github.com/phongdh262/kltn-k8s-gitops-ai/tree/main/Ha_tang/cau_hinh/06_AI_ChatOps/agent_src)

### 3.1. Pipeline GitHub Actions CI/CD 6 Giai đoạn & GHCR:
- Tài liệu cấu hình: [Ha_tang/cau_hinh/08_HITL_GitOps_CICD/01_cicd_ghcr_setup.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/08_HITL_GitOps_CICD/01_cicd_ghcr_setup.md)
- Workflow CI/CD: [.github/workflows/build-chatops-agent.yml](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/.github/workflows/build-chatops-agent.yml)
- Ảnh minh chứng:
  - Pipeline GitHub Actions 6 giai đoạn & GHCR: [`github-actions-6stages-ghcr.png`](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/08_HITL_GitOps_CICD/images/github-actions-6stages-ghcr.png)

### 3.2. Phân quyền HITL Phạm vi Hẹp & Self-Managed Argo CD:
- Tài liệu triển khai: [Ha_tang/cau_hinh/08_HITL_GitOps_CICD/02_argocd_self_managed_setup.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/08_HITL_GitOps_CICD/02_argocd_self_managed_setup.md)
- Manifest & cấu hình Argo CD:
  - [02-chatops-deployment.yaml](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/06_AI_ChatOps/manifests/02-chatops-deployment.yaml)
  - [05-hitl-scoped-roles.yaml](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/06_AI_ChatOps/manifests/05-hitl-scoped-roles.yaml)
  - [application-chatops-agent.yaml](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/06_AI_ChatOps/configs/application-chatops-agent.yaml)
- Ảnh minh chứng:
  - Argo CD đồng bộ `web-app-gitops` & `chatops-agent-gitops`: [`argocd-two-apps-synced.png`](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/08_HITL_GitOps_CICD/images/argocd-two-apps-synced.png)

### 3.3. Kiểm thử Phê duyệt HITL GitOps & Nhật ký Kiểm toán (`/audit`):
- Tài liệu kiểm thử: [Ha_tang/cau_hinh/08_HITL_GitOps_CICD/00_kiem_tra_hitl_audit.md](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/08_HITL_GitOps_CICD/00_kiem_tra_hitl_audit.md)
- Ảnh minh chứng:
  - Phê duyệt HITL tăng replica chuẩn GitOps trên Telegram: [`telegram-hitl-gitops-scale.png`](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/08_HITL_GitOps_CICD/images/telegram-hitl-gitops-scale.png)
  - Nhật ký kiểm toán `/audit` trên Telegram: [`telegram-audit-log.png`](https://github.com/phongdh262/kltn-k8s-gitops-ai/blob/main/Ha_tang/cau_hinh/08_HITL_GitOps_CICD/images/telegram-audit-log.png)

---

## 4. Khai báo sử dụng AI
- **Tên công cụ & Phiên bản:** Gemini , model 3.8 flash
- **Mục đích:** Hỗ trợ thiết kế bộ kiểm thử `pytest`, workflow GitHub Actions 6 giai đoạn, manifest `Role` phân quyền hẹp cho cơ chế HITL và mô-đun `ActionGovernanceStore`.
- **Phần AI hỗ trợ/tạo ra:**
  - Bộ kiểm thử `test_config_security.py`, `test_webhooks.py`, `test_hitl.py`, workflow `build-chatops-agent.yml`, manifest `05-hitl-scoped-roles.yaml` và `application-chatops-agent.yaml`.
- **Phần sinh viên tự thực hiện và kiểm chứng:**
  - Tạo GitHub Fine-grained PAT, cấu hình quyền truy cập Package trên GHCR, thực hiện kiểm thử HITL trên Telegram và kiểm tra trạng thái đồng bộ trên Argo CD.
  - Cấu hình biến môi trường bắt buộc (`ALLOWED_USER_IDS`, `WEBHOOK_SECRET`) và tham số GitOps trong `02-chatops-deployment.yaml`.

---

## 5. Kế hoạch Tuần 8
1. Xây dựng ứng dụng Web FastAPI kết nối cơ sở dữ liệu **PostgreSQL** trên VPS 01 qua giao diện WireGuard (`10.10.0.1:5432`).
2. Triển khai `postgres-exporter` kết nối Prometheus (VPS 03) thu thập chỉ số hoạt động của cơ sở dữ liệu.
