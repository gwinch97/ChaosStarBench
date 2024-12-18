#!/bin/bash

cpus=$1
mem=$2
n_nodes=$3
n_inst=$4

# Startup minikube cluster
echo "----- START MINIKUBE -----"
status=$(minikube status --format='{{.Host}}')
if [[ "$status" == "Running" ]]; then
	echo "Minikube is already running"
else
	minikube start --cpus=${cpus} --memory=${mem} --extra-config=kubelet.housekeeping-interval=1s --nodes ${n_nodes}
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

# Setup deployment
echo "----- SETUP DEPLOYMENT -----"
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

# Start requried port-forwarding
echo "----- PORT FORWARDING -----"
sleep 5
screen -ls | grep "\.kube-tunnel[[:space:]]" > /dev/null
if [ $? -ne 0 ]; then
	echo "Ports for kube tunnel forwarded"
	screen -dmS kube-tunnel bash -c "minikube tunnel; exec bash" 
else
	echo "Ports for kube tunnel already forwarded"
fi

screen -ls | grep "\.chaos-pf[[:space:]]" > /dev/null
if [ $? -ne 0 ]; then
	echo "Ports for chaos forwarded"
	screen -dmS chaos-pf bash -c "./pod_running_check.sh 'chaos-mesh' 'chaos-dashboard'; helm upgrade chaos-mesh chaos-mesh/chaos-mesh --namespace=chaos-mesh --version 2.6.3 --set dashboard.securityMode=false; kubectl config set-context --current --namespace=chaos-mesh; kubectl get pods | grep chaos-dashboard | awk '{print \$1}' | xargs -I {} kubectl port-forward {} 2333"
else
	echo "Ports for chaos already forwarded"
fi

screen -ls | grep "\.jaeger-pf[[:space:]]" > /dev/null
if [ $? -ne 0 ]; then
	echo "Ports for jaeger forwarded"		
	screen -dmS jaeger-pf bash -c "./pod_running_check.sh 'socialnetwork' 'jaeger'; kubectl config set-context --current --namespace=socialnetwork; kubectl get pods | grep jaeger | awk '{print \$1}' | xargs -I {} kubectl port-forward {} 16686:16686"
else
	echo "Ports for jaeger already forwarded"
fi

screen -ls | grep "\.prom-pf[[:space:]]" > /dev/null
if [ $? -ne 0 ]; then
	echo "Ports for prometheus forwarded"
	screen -dmS prom-pf bash -c "./pod_running_check.sh 'monitoring' 'prometheus-server'; kubectl config set-context --current --namespace=monitoring; kubectl get pods | grep prometheus-server | awk '{print \$1}' | xargs -I {} kubectl port-forward {} 9090"
else
	echo "Ports for prometheus already forwarded"
fi

# Deploy and patch Metrics Server for autoscaling
echo "----- DEPLOY METRICS SERVER -----"
kubectl config set-context --current --namespace=socialnetwork
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Allow metrics server to run without TLS
echo "----- PATCH METRICS SERVER -----"
kubectl patch deploy metrics-server -n kube-system --type='json' -p='[{"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--kubelet-insecure-tls=true"}]'