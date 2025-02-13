#!/bin/bash

# download tar.gz
curl -fsSLO https://mirrors.chaos-mesh.org/chaosd-v1.4.0-linux-amd64.tar.gz
tar zxvf chaosd-v1.4.0-linux-amd64.tar.gz && sudo mv chaosd-v1.4.0-linux-amd64 /usr/local/

# update PATH
echo 'export PATH=$PATH:/usr/local/chaosd-v1.4.0-linux-amd64' >> ~/.bashrc
source ~/.bashrc

# cleanup
rm chaosd-v1.4.0-linux-amd64.tar.gz
echo "Success: chaosd installed successfully."