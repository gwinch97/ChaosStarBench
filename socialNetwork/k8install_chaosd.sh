#!/bin/bash

curl -fsSLO https://mirrors.chaos-mesh.org/chaosd-v1.4.0-linux-amd64.tar.gz
tar zxvf chaosd-v1.4.0-linux-amd64.tar.gz && sudo mv chaosd-v1.4.0-linux-amd64 /usr/local/
export PATH=/usr/local/chaosd-v1.4.0-linux-amd64:$PATH
rm chaosd-v1.4.0-linux-amd64.tar.gz
echo "Success: chaosd installed successfully."