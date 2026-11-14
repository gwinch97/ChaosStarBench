#!/bin/bash

cpus=$1
mem=$2
n_nodes=$3
n_inst=$4

usage() {
  cat <<EOF
Usage: $(basename "$0") [cpus mem n_nodes n_inst]

Options:
  -cpus     Number of cpu cores per node
  -mem      Amount of memory to allocate per node
  -n_nodes  Number of virtual nodes in total
  -n_inst   Number of instances to start the deployment with
EOF
  exit 1
}

if [[ $# -eq 0 ]]; then
	usage
fi

if [ "$n_nodes" -lt 2 ]; then
	echo "ERROR: running socialnetwork with less than 2 nodes causes instability"
	exit 0
fi

# Startup minikube cluster
echo "----- START MINIKUBE -----"

status=$(minikube status --format='{{.Host}}')

if [ "$status" == "Running" ]; then
	echo "Minikube is already running"
else
	minikube start \
		--kubernetes-version=v1.28.6 \
		--driver=docker \
		--cpus="${cpus}" \
		--memory="${mem}" \
		--extra-config=kubelet.housekeeping-interval=1s \
		--extra-config=kubelet.fail-swap-on=false \
		--nodes="${n_nodes}"
		# Increase open-file descriptors limit for chaos-mesh
fi

echo "----- TAINT CONTROL-PLANE NODE -----"
kubectl taint node minikube node-role.kubernetes.io/control-plane=:NoSchedule --overwrite || true

# Fix for persistant volumes permission issue for >1 node clusters (issue#12360)
echo "----- FIX PERMISSION ISSUE -----"
minikube addons disable storage-provisioner
minikube addons disable default-storageclass
minikube addons enable volumesnapshots
minikube addons enable csi-hostpath-driver

# Recreate the CSI HostPath StorageClass so we can set volumeBindingMode
echo "----- RECREATE CSI HOSTPATH STORAGECLASS -----"
# 1) Remove the old class (ignore errors)
kubectl delete storageclass csi-hostpath-sc || true

# 2) Recreate it with WaitForFirstConsumer + default marker
cat <<EOF | kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: csi-hostpath-sc
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"
provisioner: hostpath.csi.k8s.io
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Delete
allowVolumeExpansion: true
EOF

# Create host directory in minikube
echo "----- CREATE LOCAL DIRECTORY ON MINIKUBE (/data/prometheus) -----"
minikube ssh -- "sudo mkdir -p /data/prometheus && sudo chown docker:docker /data/prometheus"

# emit local PV manifest and apply
echo "----- CREATE A LOCAL-PV FOR PROMETHEUS ON minikube -----"
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolume
metadata:
  name: prometheus-minikube-local-pv
spec:
  capacity:
    storage: 24Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Delete
  storageClassName: csi-hostpath-sc
  volumeMode: Filesystem
  local:
    path: /data/prometheus
  nodeAffinity:
    required:
      nodeSelectorTerms:
        - matchExpressions:
            - key: kubernetes.io/hostname
              operator: In
              values:
                - minikube
EOF

# Create kubectl namespaces and install helm charts to them
echo "----- CREATE KUBECTL NAMESPACES -----"
cd helm-chart
if kubectl get namespace "socialnetwork" > /dev/null 2>&1; then
	echo "Namespace socialnetwork exists"
else
	kubectl create namespace socialnetwork
	kubectl config set-context --current --namespace=socialnetwork
	helm install socialnetwork ./socialnetwork
	kubectl create configmap jaeger-sampling-strategy --from-file=../../jaeger/sampling-strategy.json
fi

cd ../.. # back to ChaosStarBench folder
if kubectl get namespace "prometheus" > /dev/null 2>&1; then
	echo "Namespace prometheus exists"
else
	kubectl create namespace prometheus
	kubectl config set-context --current --namespace=prometheus
	helm install prometheus ./prometheus
fi

if kubectl get namespace "chaos-mesh" > /dev/null 2>&1; then
	helm install prometheus ./prometheus
fi

if kubectl get namespace "chaos-mesh" > /dev/null 2>&1; then
    echo "Namespace chaos-mesh exists"
else
	kubectl create namespace chaos-mesh
	kubectl config set-context --current --namespace=chaos-mesh
	helm install chaos-mesh ./chaos-mesh --set dashboard.securityMode=false
fi
cd socialNetwork


echo "----- CHECKING FOR MINIKUBE CHAOSD INSTALL -----"
minikube cp ./k8install_chaosd.sh /home/docker/
minikube ssh -- "bash ./k8install_chaosd.sh"
# to install on user's machine, run 'bash ./install_chaosd.sh'

echo "----- WAITING FOR JAEGER DEPLOYMENT -----"
bash ./k8pod_check.sh "socialnetwork" "elasticsearch"
bash ./k8pod_check.sh "socialnetwork" "jaeger-query"

# Scale socialnetwork deployment
if [ "$n_inst" -gt 1 ]; then
	echo "----- SCALE DEPLOYMENT -----"
	for deploy in $(kubectl get deploy -n socialnetwork -o name); do
		if [ "$deploy" == *"jaeger"* ] || [ "$deploy" == *"mongodb"* ] || [ "$deploy" == *"media-frontend"* ] || [ "$deploy" == *"nginx"* ] || [ "$deploy" == *"redis"* ] || [ "$deploy" == *"memcache"* ]; then
			continue
		fi
		kubectl scale --replicas=${n_inst} $deploy -n socialnetwork;
	done
fi

echo "----- PORT FORWARDING -----"
# End all existing port forwarding screens
SESSION_NAMES=("api-pf" "chaos-pf" "es-pf" "jaeger-pf" "prom-pf")
for SESSION_NAME in "${SESSION_NAMES[@]}"; do
    if screen -list | grep -q "\.${SESSION_NAME}"; then
        screen -X -S "$SESSION_NAME" quit
    fi
done

# Create new port forwards
screen -dmS api-pf bash -c "./k8pod_check.sh socialnetwork nginx-thrift; minikube tunnel; exec bash"
screen -dmS chaos-pf bash -c "./k8pod_check.sh chaos-mesh chaos-dashboard; kubectl get pods -n chaos-mesh | grep 'chaos-dashboard' | awk '{print \$1}' | xargs -I {} kubectl port-forward -n chaos-mesh {} 2333:2333; exec bash"
screen -dmS es-pf bash -c "kubectl get pods -n socialnetwork | grep 'socialnetwork-elasticsearch' | awk '{print \$1}' | xargs -I {} kubectl port-forward -n socialnetwork {} 9200:9200; exec bash"
screen -dmS jaeger-pf bash -c "./k8pod_check.sh socialnetwork jaeger-query; kubectl get pods -n socialnetwork | grep 'jaeger-query' | awk '{print \$1}' | xargs -I {} kubectl port-forward -n socialnetwork {} 16686:16686; exec bash"
screen -dmS prom-pf bash -c "./k8pod_check.sh prometheus prometheus-server; kubectl get pods -n prometheus | grep 'prometheus-server' | awk '{print \$1}' | xargs -I {} kubectl port-forward -n prometheus {} 9090:9090; exec bash"
echo "Created new screens to forward all ports"

# Deploy and patch Metrics Server for autoscaling
echo "----- DEPLOY METRICS SERVER -----"
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Allow metrics server to run without TLS
