# TRIỂN KHAI GITOPS VỚI ARGO CD

## 1. Khái niệm và Nguyên lý cốt lõi

Trong các phương pháp triển khai ứng dụng trên Kubernetes, GitOps là mô hình triển khai và vận hành hiện đại, sử dụng Git làm nơi lưu trữ và quản lý cấu hình chính thức. Thông qua các công cụ GitOps như Argo CD hoặc Flux CD, hệ thống có thể tự động đồng bộ trạng thái ứng dụng trên Kubernetes theo cấu hình được khai báo trong Git.

Các cấu hình mô tả trạng thái mong muốn của hệ thống (Desired State), bao gồm các tài nguyên Kubernetes như Deployment, Service, ConfigMap và Ingress, được lưu trữ dưới dạng tệp YAML trong Git Repository và quản lý phiên bản thông qua Git. Điều này giúp theo dõi lịch sử thay đổi, kiểm soát cấu hình và khôi phục phiên bản trước đó khi cần thiết.


## 2. So sánh CI/CD Push-based và GitOps Pull-based


| Tiêu chí so sánh | CI/CD Push-based | GitOps Pull-based | Nhận xét áp dụng |
| :--- | :--- | :--- | :--- |
| **Bảo mật** | Phải đưa file cấu hình `kubeconfig` chứa quyền admin lên secrets của CI bên ngoài. | **Cụm Kubernetes khép kín 100%**: Argo CD nằm bên trong cluster tự kéo manifest về, không mở cổng API ra ngoài. | **Chọn Argo CD**: Đảm bảo an toàn cho mô hình đa VPS. |
| **Phát hiện lệch cấu hình** | Không biết nếu có người can thiệp trực tiếp bằng lệnh `kubectl edit/delete`. | Tự động phát hiện: Trạng thái chuyển sang `OutOfSync` và có thể tự động hoàn nguyên (`Auto-heal`). | Giúp hệ thống chuẩn xác theo đúng khai báo trên Git. |
| **Cơ chế Rollback** | Kích hoạt lại pipeline build CI cũ, mất nhiều thời gian. | Rollback tức thì: Chỉ cần revert commit trên Git hoặc bấm nút trên giao diện Argo CD. | Phục vụ trực tiếp cho kịch bản đo thời gian phục hồi dịch vụ. |
| **Lịch sử thay đổi (Audit Log)** | Phân tán trên các log của công cụ CI. | Lưu trên Git Commit History | Minh bạch cho việc báo cáo và nghiệm thu. |

---

## 3. Kế hoạch triển khai Argo CD

- **Vị trí cài đặt:** Triển khai trên **VPS 02 (Worker 1)**, tách biệt tải với Master và hệ thống giám sát.
- **Cơ chế hoạt động:** Kết nối với Git repository qua HTTPS/SSH, thiết lập chính sách tự động đồng bộ (Automated Sync Policy), tính năng `selfHeal: true` và `prune: true` để dọn dẹp các tài nguyên bị xóa bỏ trên Git.

---

## 4. Tài liệu tham khảo
1. **Tuyên ngôn nguyên lý GitOps (OpenGitOps Standard - CNCF):** https://opengitops.dev/
2. **Tài liệu chính thức Argo CD Documentation:** https://argo-cd.readthedocs.io/en/stable/
3. **Mã nguồn Argo CD trên GitHub (CNCF Graduated Project):** https://github.com/argoproj/argo-cd
4. **GitOps - Operations by Pull Request (Alexis Richardson - Weaveworks):** https://www.weave.works/blog/gitops-operations-by-pull-request
5. **So sánh Push-based vs Pull-based CI/CD:** https://about.gitlab.com/topics/gitops/

