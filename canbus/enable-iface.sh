# reset the interface (harmless if it was already down)
sudo ip link set can0 down

# program the nominal (arbitration-phase) bitrate ONLY
sudo ip link set can0 type can bitrate 250000 restart-ms 100

# now bring it up
sudo ip link set can0 up

# confirm that it is up
ip -details -brief link show can0
# can0:  NOARP  state UP  mtu 16  qdisc pfifo_fast mode DEFAULT
#         link/can  bitrate 250000  restart-ms 100  ...

