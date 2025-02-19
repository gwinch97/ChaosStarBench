#!/bin/bash

# download tar.gz
curl -fsSL -o chaosd-v1.4.0-linux-amd64.tar.gz https://mirrors.chaos-mesh.org/chaosd-v1.4.0-linux-amd64.tar.gz

# unzip tar.gz
tar zxvf chaosd-v1.4.0-linux-amd64.tar.gz && cd chaosd-v1.4.0-linux-amd64/

# install all tools to user's system (except byteman - this project does not need JVM chaos)
sudo install -o root -g root -m 0755 chaosd /usr/local/bin/chaosd
cd tools/
sudo install -o root -g root -m 0755 FileTool /usr/local/bin/FileTool
sudo install -o root -g root -m 0755 memStress /usr/local/bin/memStress
sudo install -o root -g root -m 0755 PortOccupyTool /usr/local/bin/PortOccupyTool
sudo install -o root -g root -m 0755 stress-ng /usr/local/bin/stress-ng
sudo install -o root -g root -m 0755 tproxy /usr/local/bin/tproxy

# cleanup
cd ../../
rm -rf chaosd-v1.4.0-linux-amd64/
rm chaosd-v1.4.0-linux-amd64.tar.gz

if command -v chaosd &>/dev/null; then
    echo "Success: Chaosd tools installed successfully."
else
    echo "Error: Chaosd was NOT installed successfully."
fi