# VPS 01 (k3s-master)

- **IP**: 103.110.86.106
- **Hostname:** `k3s-master`
- **Vai trò:** K3s Server, Ingress Traefik, Database

---

## 1. Các lệnh cấu hình trên VPS 01
```bash
# Đổi hostname
sudo hostnamectl set-hostname k3s-master
exec bash

# Cập nhật OS & Cài gói công cụ
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git jq vim iptables socat conntrack iproute2 net-tools wireguard wireguard-tools

# Tắt Swap
sudo swapoff -a
sudo sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab

# Nạp Kernel Modules
cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF
sudo modprobe overlay
sudo modprobe br_netfilter

# Nạp Sysctl
cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward = 1
EOF
sudo sysctl --system

# Đồng bộ thời gian Việt Nam
sudo timedatectl set-timezone Asia/Ho_Chi_Minh
sudo timedatectl set-ntp on
```

---

## 2. Kết quả kiểm tra

*Kiểm tra Hostname:*
```bash
hostnamectl
```
![alt text](image.png)

*Kiểm tra Swap):*
```bash
free -h
```
![alt text](image-1.png)

*Kiểm tra Kernel Modules & IP Forward:*
```bash
lsmod | grep -E 'overlay|br_netfilter'
sysctl net.ipv4.ip_forward
```
![alt text](image-2.png)