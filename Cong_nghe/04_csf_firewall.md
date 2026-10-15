# BẢO MẬT HẠ TẦNG VỚI CSF VÀ LFD FIREWALL

## 1. Vấn đề an toàn bảo máy chủ
Trên môi trường máy chủ cloud, các VPS có IP công khai liên tục phải hứng chịu hàng ngàn cuộc tấn công tự động mỗi ngày từ các botnet trên Internet:
- Tấn công dò quét mật khẩu SSH (SSH Brute-force).
- Quét các cổng dịch vụ mở (Port Scanning).
- Tấn công từ chối dịch vụ nhẹ (SYN Flood DoS).

Nếu chỉ dùng tường lửa cơ bản như UFW (Uncomplicated Firewall), quản trị  có thể mở hoặc đóng cổng thụ động, không có cơ chế tự động ngăn chặn và khóa IP (IP Banning) của kẻ tấn công.


## 2. So sánh CSF Firewall vs UFW

| Tiêu chí | UFW (Uncomplicated Firewall) | CSF (ConfigServer Security & Firewall) + LFD | Nhận xét & Đánh giá |
| :--- | :--- | :--- | :--- |
| **Công nghệ** | Dòng lệnh cơ bản bọc quanh `iptables` | Giải pháp tường lửa Stateful Packet Inspection (SPI) kết hợp IDS/IPS | Cung cấp khả năng phòng vệ chủ động |
| **Chống Brute-force SSH** | Không hỗ trợ | Tích hợp sẵn tiến trình LFD: Tự động phát hiện và block IP sau số lần đăng nhập sai cấu hình | Tiết kiệm tài nguyên cài đặt, phối hợp chặt chẽ với tường lửa. |
| **Phát hiện quét cổng (Port Scan Tracking)** | Không hỗ trợ | Hỗ trợ mạnh mẽ: Tự động đưa IP vào danh sách đen nếu cố tình quét các cổng đóng trên VPS | Ẩn các dịch vụ nội bộ. |
| **Bảo vệ chống SYN Flood** | Cơ bản, phụ thuộc kernel | Tích hợp module SYNFLOOD Protection: Tự động giới hạn tốc độ kết nối khi có dấu hiệu tràn gói tin | Ngăn ngừa việc treo máy chủ do quá tải kết nối rác. |
| **Quản lý danh sách trắng (Whitelist)** | Cần gõ nhiều lệnh ufw allow rời rạc | File cấu hình tập trung (`csf.allow`, `csf.conf`, `csf.ignore`) | Thuận tiện để whitelist toàn bộ dải mạng WireGuard (`10.10.0.0/24`). |


## 3. Cấu hình CSF áp dụng cho 3 VPS

1. **Gỡ bỏ hoàn toàn UFW** tránh xung đột.
2. **Whitelist giao diện WireGuard (`ETH_DEVICE_SKIP = "wg0"`):** Đảm bảo lưu lượng K3s API (port 6443) và Pod Network lưu thông với tốc độ tối đa trong mạng nội bộ ảo `10.10.0.0/24`.
3. **Chính sách mở cổng công khai:**
   - **VPS 01 (Master):** Mở TCP `80`, `443` (cho Traefik Ingress) và UDP `51820` (cho WireGuard).
   - **VPS 02 & VPS 03 (Workers):** UDP `51820` (WireGuard). Không mở cổng Argo CD (8080) hay Prometheus (9090).


## 4. Tài liệu tham khảo
1. **Trang chủ chính thức ConfigServer Security & Firewall:** https://configserver.dev/configserver-security-firewall/
2. **Tài liệu hướng dẫn cài đặt và cấu hình CSF/LFD:** https://download.configserver.com/csf/install.txt
3. **Tài liệu Linux Iptables và Netfilter Architecture:** https://netfilter.org/documentation/
4. **Hướng dẫn bảo mật máy chủ Ubuntu Server Guide:** https://ubuntu.com/server/docs/security-firewall

