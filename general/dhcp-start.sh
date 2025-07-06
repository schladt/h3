#!/bin/bash

# Set static IP on eth1
echo "[*] Setting static IP on eth1 to 192.168.0.1/24..."
sudo ip addr flush dev eth1
sudo ip addr add 192.168.0.1/24 dev eth1
sudo ip link set eth1 up
# Kill any existing dnsmasq
echo "[*] Killing existing dnsmasq instances (if any)..."
sudo pkill dnsmasq

# Start dnsmasq DHCP server
echo "[*] Starting dnsmasq DHCP server on eth1..."
sudo dnsmasq --interface=eth1 --bind-interfaces --dhcp-range=192.168.0.101,192.168.0.111,12h
echo "[✓] Network setup complete. DHCP serving on eth1 from 192.168.0.101 to 192.168.0.111."

# to check current leases
# sudo cat /var/lib/misc/dnsmasq.leases
