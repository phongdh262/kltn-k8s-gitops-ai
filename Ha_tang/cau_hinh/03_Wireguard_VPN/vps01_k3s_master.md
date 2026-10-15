# CẤU HÌNH, KẾT NỐI WIREGUARD VPN CHO VPS 01 (k3s-master)

- **IP**: 103.110.86.106
- **Hostname:** `k3s-master`
- **IP WireGuard (`wg0`):** `10.10.0.1/24`
- **Port UDP lắng nghe:** `51820`

---

## 1. Cài đặt và tạo cặp khóa trên VPS 01
```bash
sudo apt update && sudo apt install -y wireguard wireguard-tools
cd /etc/wireguard
umask 077
wg genkey | tee privatekey | wg pubkey > publickey

# Xem key:
cat privatekey
cat publickey
```

---

## 2. File cấu hình `/etc/wireguard/wg0.conf`

Tạo file `/etc/wireguard/wg0.conf`:
```ini
[Interface]
Address = 10.10.0.1/24
ListenPort = 51820
PrivateKey = <PRIVATE_KEY_VPS01>

# Peer: VPS 02 (Worker 1)
[Peer]
PublicKey = <PUBLIC_KEY_VPS02>
AllowedIPs = 10.10.0.2/32
Endpoint = 103.110.85.111:51820
PersistentKeepalive = 25

# Peer: VPS 03 (Worker 2)
[Peer]
PublicKey = <PUBLIC_KEY_VPS03>
AllowedIPs = 10.10.0.3/32
Endpoint = 103.110.85.145:51820
PersistentKeepalive = 25
```

---

## 3. Khởi động và Kiểm tra kết nối
```bash
# Kích hoạt service
sudo systemctl enable --now wg-quick@wg0

# Xem trạng thái WireGuard
sudo wg show

# Ping kiểm tra Worker 1 và Worker 2
ping -c 4 10.10.0.2
ping -c 4 10.10.0.3
```
![alt text](image-1.png)
![alt text](image.png)