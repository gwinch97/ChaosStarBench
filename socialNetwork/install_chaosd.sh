#!/bin/bash

# download tar.gz
curl -fsSL -o chaosd-v1.4.0-linux-amd64.tar.gz https://mirrors.chaos-mesh.org/chaosd-v1.4.0-linux-amd64.tar.gz

# unzip tar.gz
tar zxvf chaosd-v1.4.0-linux-amd64.tar.gz && cd chaosd-v1.4.0-linux-amd64/

# install to user's system
sudo install -o root -g root -m 0755 chaosd /usr/local/bin/chaosd

if command -v chaosd &>/dev/null; then
    echo "Success: Chaosd installed successfully."
else
    echo "Error: Chaosd was NOT installed successfully."
fi