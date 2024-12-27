#!/bin/bash

cpus=$1
mem=$2
n_nodes=$3
n_inst=$4

# Startup minikube cluster
echo "----- START MINIKUBE -----"
if [ "$n_nodes" -lt 2 ]; then
	echo "WARNING: running socialnetwork with less than 2 nodes may cause instability"
fi

status=$(minikube status --format='{{.Host}}')

if [[ "$status" == "Running" ]]; then
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

# Create kubectl namespaces
echo "----- CREATE KUBECTL NAMESPACES -----"
bash k8setup.sh

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

# Start required port-forwarding
echo "----- PORT FORWARDING -----"

# End all existing port forwarding screens
SESSION_NAMES=("kube-tunnel" "chaos-pf" "jaeger-pf" "prom-pf" "es-pf")
for SESSION_NAME in "${SESSION_NAMES[@]}"; do
    if screen -list | grep -q "\.${SESSION_NAME}"; then
        screen -X -S "$SESSION_NAME" quit
		echo "Quit open screen $SESSION_NAME"
    fi
done

# Forward ports
screen -dmS kube-tunnel bash -c "minikube tunnel; exec bash"
screen -dmS chaos-pf bash -c "./pod_running_check.sh 'chaos-mesh' 'chaos-dashboard'; kubectl get pods -n chaos-mesh | grep 'chaos-dashboard' | awk '{print \$1}' | xargs -I {} kubectl port-forward -n chaos-mesh {} 2333:2333; exec bash"
screen -dmS prom-pf bash -c "./pod_running_check.sh 'monitoring' 'prometheus-server'; kubectl get pods -n monitoring | grep 'prometheus-server' | awk '{print \$1}' | xargs -I {} kubectl port-forward -n monitoring {} 9090:9090; exec bash"
screen -dmS es-pf bash -c "kubectl get pods -n socialnetwork | grep 'socialnetwork-elasticsearch' | awk '{print \$1}' | xargs -I {} kubectl port-forward -n socialnetwork {} 9200:9200; exec bash"
screen -dmS jaeger-pf bash -c "kubectl get pods -n socialnetwork | grep 'jaeger-query' | awk '{print \$1}' | xargs -I {} kubectl port-forward -n socialnetwork {} 16686:16686; exec bash"
echo "Created new screens to forward all ports"

# Deploy and patch Metrics Server for autoscaling
echo "----- DEPLOY METRICS SERVER -----"
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Allow metrics server to run without TLS
echo "----- PATCH METRICS SERVER -----"
kubectl patch deploy metrics-server -n kube-system --type='json' -p='[{"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--kubelet-insecure-tls=true"}]'