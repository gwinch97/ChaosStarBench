#!/bin/bash

cpus=$1
mem=$2
n_nodes=$3
n_inst=$4

# Startup minikube cluster
status=$(minikube status --format='{{.Host}}')
if [[ "$status" == "Running" ]]; then
	echo "Minikube is already running"
else
	minikube start --cpus=${cpus} --memory=${mem} --extra-config=kubelet.housekeeping-interval=1s --nodes ${n_nodes}
fi

# kubectl taint nodes minikube key=monitoring:NoSchedule
# Fix for persistant volumes permission issue for >1 node clusters (issue#12360)
minikube addons disable storage-provisioner
minikube addons disable default-storageclass
minikube addons enable volumesnapshots
minikube addons enable csi-hostpath-driver
kubectl patch storageclass csi-hostpath-sc -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'

# Setup deployment
if kubectl get namespace "socialnetwork" > /dev/null 2>&1; then
	echo "Namespace socialnetwork exists."
else
	kubectl create namespace socialnetwork
	kubectl config set-context --current --namespace=socialnetwork
	cd helm-chart
	helm install v1 socialnetwork
fi

if kubectl get namespace "monitoring" > /dev/null 2>&1; then
	echo "Namespace monitoring exists."
else
	cd ../..
	kubectl create namespace monitoring
	kubectl config set-context --current --namespace=monitoring
	helm install cadvisor ./cadvisor
	helm install prometheus ./prometheus
	kubectl create configmap jaeger-sampling-strategy --from-file=jaeger/sampling-strategy.json
	kubectl config set-context --current --namespace=default
	#helm install jaeger jaegertracing/jaeger -f jaeger/values.yaml
fi

if kubectl get namespace "chaos-mesh" > /dev/null 2>&1; then
        echo "Namespace chaos-mesh exists."
else
	kubectl create namespace chaos-mesh
	kubectl config set-context --current --namespace=chaos-mesh
	helm install chaos-mesh ./chaos-mesh
fi

# Scale socialnetwork deployment
if [ "$n_inst" -gt 1 ]; then
	for deploy in $(kubectl get deploy -n socialnetwork -o name); do
		if [[ "$deploy" == *"jaeger"* ]] || [[ "$deploy" == *"mongodb"* ]] || [[ "$deploy" == *"media-frontend"* ]] || [[ "$deploy" == *"nginx"* ]] || [[ "$deploy" == *"redis"* ]] || [[ "$deploy" == *"memcache"* ]]; then
			continue
		fi
		kubectl scale --replicas=${n_inst} $deploy -n socialnetwork;
	done
fi

# Start requried port-forwarding
screen -ls | grep "\.kube-tunnel[[:space:]]" > /dev/null
if [ $? -ne 0 ]; then
	screen -dmS kube-tunnel bash -c "minikube tunnel; exec bash" 
fi

screen -ls | grep "\.prom-pf[[:space:]]" > /dev/null
if [ $? -ne 0 ]; then
	screen -dmS prom-pf bash -c "./pod_running_check.sh 'monitoring' 'prometheus-server'; kubectl config set-context --current --namespace=monitoring; kubectl get pods | grep prometheus-server | awk '{print \$1}' | xargs -I {} kubectl port-forward {} 9090"
fi

screen -ls | grep "\.chaos-pf[[:space:]]" > /dev/null
if [ $? -ne 0 ]; then
	screen -dmS chaos-pf bash -c "./pod_running_check.sh 'chaos-mesh' 'chaos-dashboard'; helm upgrade chaos-mesh chaos-mesh/chaos-mesh --namespace=chaos-mesh --version 2.6.3 --set dashboard.securityMode=false; kubectl config set-context --current --namespace=chaos-mesh; kubectl get pods | grep chaos-dashboard | awk '{print \$1}' | xargs -I {} kubectl port-forward {} 2333"
fi

screen -ls | grep "\.jaeger-pf[[:space:]]" > /dev/null
if [ $? -ne 0 ]; then
	screen -dmS jaeger-pf bash -c "./pod_running_check.sh 'socialnetwork' 'jaeger'; kubectl config set-context --current --namespace=socialnetwork; kubectl get pods | grep jaeger | awk '{print \$1}' | xargs -I {} kubectl port-forward {} 16686:16686"
fi

# Deploy and patch Metrics Server for autoscaling
kubectl config set-context --current --namespace=socialnetwork
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
kubectl patch deploy metrics-server -n kube-system --type='json' -p='[{"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--kubelet-insecure-tls=true"}]'