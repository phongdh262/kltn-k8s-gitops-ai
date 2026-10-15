# MẠNG RIÊNG ẢO WIREGUARD

---

## 1. Vấn đề an toàn mạng khi cụm Kubernetes chạy trên đa VPS
Khi thuê các VPS từ nhà cung cấp dịch vụ đám mây (mỗi máy có một IP Public riêng biệt: `103.110.85.106`, `103.110.85.111`, `103.110.85.145`) không có mạng LAN ảo nội bộ, kết nối cụm trực tiếp qua Internet công cộng sẽ gặp các rủi ro:
1. **Lộ cổng quản trị K3s API (`6443`) và Kubelet (`10250`):** Máy chủ dễ bị bot tự động trên Internet quét cổng và dò mật khẩu.
2. **Dữ liệu Pod-to-Pod không được bảo vệ:** Lưu lượng trao đổi giữa các microservices và database khi đi qua mạng Internet public có nguy cơ bị nghe lén hoặc giả mạo.

---

## 2. So sánh các giải pháp mạng riêng ảo (VPN / Overlay)


| Giải pháp | Cơ chế hoạt động | Ưu điểm | Nhược điểm | Đánh giá áp dụng |
| :--- | :--- | :--- | :--- | :--- |
| **Mở Firewall trực tiếp** | Mở toàn bộ cổng K8s trên IP Public | Cài đặt nhanh , không tốn tài nguyên | Nguy cơ bảo mật nghiêm trọng, toàn bộ dữ liệu đi qua Internet không được mã hóa | **Loại bỏ** |
| **OpenVPN / IPsec** | VPN truyền thống | Công nghệ lâu đời | Cấu hình rất phức tạp, tiêu tốn CPU lớn, độ trễ cao và giảm băng thông mạng | **Loại bỏ** |
| **Tailscale / ZeroTier** | Mesh VPN dựa trên WireGuard có server điều phối trung gian (Control plane đám mây) | Dễ cấu hình, tự vượt NAT | Phụ thuộc vào bên thứ ba; phụ thuộc đường truyền quốc tế; giới hạn tính tự chủ | **Không khuyến nghị** |
| **WireGuard Full Mesh (Tự thiết lập)** | Giao thức mã hóa hiện đại chạy trực tiếp trong nhân **Linux Kernel** | **Độ trễ gần bằng 0, thông lượng tối đa, mã hóa ChaCha20-Poly1305, tự chủ** | Cấu hình thủ công cặp khóa và danh sách Peer giữa các node | **Phù hợp** |

---

## 3. Kiến trúc mạng WireGuard Full Mesh.

- **Mạng riêng ảo nội bộ:** Dải mạng riêng `10.10.0.0/24`.
- **Cổng giao tiếp duy nhất ra ngoài:** Port UDP `51820`.
- **IP nội bộ:**
  - VPS 01 (Master): `10.10.0.1`
  - VPS 02 (Worker 1): `10.10.0.2`
  - VPS 03 (Worker 2): `10.10.0.3`
- **Mô hình kết nối:** Full Mesh P2P (mỗi VPS kết nối mã hóa trực tiếp với 2 VPS còn lại), cấu hình `PersistentKeepalive = 25` giây, đảm bảo kênh kết nối thông suốt, không bị ngắt bởi router/firewall nhà mạng.

---

## 4. Kết luận

Giải pháp WireGuard Mesh mang lại một lớp mạng bảo mật, biến 3 VPS độc lập ngoài Internet thành một mạng LAN ảo, cho phép ẩn các cổng K3s API và Pod network.

---

## 5. Tài liệu tham khảo

1. **Trang chủ chính thức WireGuard:** https://www.wireguard.com/
2. **WireGuard Technical Whitepaper (Jason A. Donenfeld):** https://www.wireguard.com/papers/wireguard.pdf
3. **Tài liệu hướng dẫn cấu hình WireGuard Quick Start:** https://www.wireguard.com/quickstart/
4. **So sánh hiệu năng WireGuard vs OpenVPN/IPsec:** https://www.wireguard.com/performance/

