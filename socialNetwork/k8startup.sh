#!/bin/bash

cpus=$1
mem=$2
n_nodes=$3
n_inst=$4

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
	minikube start --cpus=${cpus} --memory=${mem} --extra-config=kubelet.housekeeping-interval=1s --extra-config=kubelet.fail-swap-on=false --nodes ${n_nodes}
fi

# kubectl taint nodes minikube key=monitoring:NoSchedule
# Fix for persistant volumes permission issue for >1 node clusters (issue#12360)
echo "----- FIX PERMISSION ISSUE -----"
minikube addons disable storage-provisioner
minikube addons disable default-storageclass
minikube addons enable volumesnapshots
minikube addons enable csi-hostpath-driver

echo "----- PATCH STORAGECLASS -----"
kubectl patch storageclass csi-hostpath-sc -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'

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
	echo "----- WAITING FOR JAEGER DEPLOYMENT -----"
	../pod_running_check.sh socialnetwork socialnetwork-elasticsearch-master
	../pod_running_check.sh socialnetwork jaeger-collector
	../pod_running_check.sh socialnetwork jaeger-query
	echo "Namespace socialnetwork created"
fi

cd ../.. # back to ChaosStarBench folder
if kubectl get namespace "prometheus" > /dev/null 2>&1; then
	echo "Namespace prometheus exists"
else
	kubectl create namespace prometheus
	kubectl config set-context --current --namespace=prometheus
	helm install prometheus ./prometheus
	echo "Namespace prometheus created"
fi

if kubectl get namespace "chaos-mesh" > /dev/null 2>&1; then
    echo "Namespace chaos-mesh exists"
else
	kubectl create namespace chaos-mesh
	kubectl config set-context --current --namespace=chaos-mesh
	helm install chaos-mesh ./chaos-mesh --set dashboard.securityMode=false
	echo "Namespace chaos-mesh created"
fi
cd socialNetwork

echo "----- CHECK CHAOSD INSTALL -----"
if command -v chaosd &>/dev/null; then
    echo "Success: Chaosd is already installed."
else
    echo "Warning: Chaosd is NOT installed."
	echo "You may be asked to enter your password to install Chaosd and add it to PATH."
    sudo bash ./install_chaosd.sh # runs in separate script to avoid having to sudo this script
fi

# Scale socialnetwork deployment
if [ "$n_inst" -gt 1 ]; then
	echo "----- SCALE DEPLOYMENT -----"
	for deploy in $(kubectl get deploy -n socialnetwork -o name); do
		if [[ "$deploy" == *"jaeger"* ]] || [[ "$deploy" == *"mongodb"* ]] || [[ "$deploy" == *"media-frontend"* ]] || [[ "$deploy" == *"nginx"* ]] || [[ "$deploy" == *"redis"* ]] || [[ "$deploy" == *"memcache"* ]]; then
			continue
		fi
		kubectl scale --replicas=${n_inst} $deploy -n socialnetwork;
	done
fi

# End all existing port forwarding screens
SESSION_NAMES=("api-pf" "chaos-pf" "es-pf" "jaeger-pf" "prom-pf")
for SESSION_NAME in "${SESSION_NAMES[@]}"; do
    if screen -list | grep -q "\.${SESSION_NAME}"; then
        screen -X -S "$SESSION_NAME" quit
    fi
done

# Start required port-forwarding
echo "----- PORT FORWARDING -----"
screen -dmS api-pf bash -c "./pod_running_check.sh socialnetwork nginx-thrift; kubectl get pods -n socialnetwork | grep 'nginx-thrift' | awk '{print \$1}' | xargs -I {} kubectl port-forward -n socialnetwork {} 8080:8080; exec bash"
screen -dmS chaos-pf bash -c "./pod_running_check.sh chaos-mesh chaos-dashboard; kubectl get pods -n chaos-mesh | grep 'chaos-dashboard' | awk '{print \$1}' | xargs -I {} kubectl port-forward -n chaos-mesh {} 2333:2333; exec bash"
screen -dmS es-pf bash -c "kubectl get pods -n socialnetwork | grep 'socialnetwork-elasticsearch' | awk '{print \$1}' | xargs -I {} kubectl port-forward -n socialnetwork {} 9200:9200; exec bash"
screen -dmS jaeger-pf bash -c "./pod_running_check.sh socialnetwork jaeger-query; kubectl get pods -n socialnetwork | grep 'jaeger-query' | awk '{print \$1}' | xargs -I {} kubectl port-forward -n socialnetwork {} 16686:16686; exec bash"
screen -dmS prom-pf bash -c "./pod_running_check.sh prometheus prometheus-server; kubectl get pods -n prometheus | grep 'prometheus-server' | awk '{print \$1}' | xargs -I {} kubectl port-forward -n prometheus {} 9090:9090; exec bash"
echo "Created new screens to forward all ports"

# Deploy and patch Metrics Server for autoscaling
echo "----- DEPLOY METRICS SERVER -----"
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Allow metrics server to run without TLS
echo "----- PATCH METRICS SERVER -----"
kubectl patch deploy metrics-server -n kube-system --type='json' -p='[{"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--kubelet-insecure-tls=true"}]'

kubectl config set-context --current --namespace=socialnetwork
