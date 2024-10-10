#!/bin/bash
# Startup minikube cluster
status=$(minikube status --format='{{.Host}}')
if [[ "$status" == "Running" ]]; then
	echo "Minikube is already running"
else
	minikube start --cpus=2 --memory=3815 --extra-config=kubelet.housekeeping-interval=1s --nodes 4
fi

# Setup deployment
bash setup-k8.sh

# Scale socialnetwork deployment
for deploy in $(kubectl get deploy -n socialnetwork -o name); do
	if [[ "$deploy" == *"jaeger"* ]] || [[ "$deploy" == *"mongodb"* ]] || [[ "$deploy" == *"media-frontend"* ]] || [[ "$deploy" == *"nginx"* ]] || [[ "$deploy" == *"redis"* ]] || [[ "$deploy" == *"memcache"* ]]; then
		continue
	fi
	kubectl scale --replicas=1 $deploy -n socialnetwork;
done

sleep 60

# Start requried port-forwarding
screen -ls | grep "\.kube-tunnel[[:space:]]" > /dev/null
if [ $? -ne 0 ]; then
	screen -dmS kube-tunnel bash -c "minikube tunnel; exec bash" 
fi
sleep 5

screen -ls | grep "\.prom-pf[[:space:]]" > /dev/null
if [ $? -ne 0 ]; then
	screen -dmS prom-pf bash -c "kubectl config set-context --current --namespace=monitoring; kubectl get pods | grep prometheus-server | awk '{print \$1}' | xargs -I {} kubectl port-forward {} 9090"
fi
sleep 5

screen -ls | grep "\.chaos-pf[[:space:]]" > /dev/null
if [ $? -ne 0 ]; then
	screen -dmS chaos-pf bash -c "helm upgrade chaos-mesh chaos-mesh/chaos-mesh --namespace=chaos-mesh --version 2.6.3 --set dashboard.securityMode=false; kubectl config set-context --current --namespace=chaos-mesh; kubectl get pods | grep chaos-dashboard | awk '{print \$1}' | xargs -I {} kubectl port-forward {} 2333"
fi
sleep 5

screen -ls | grep "\.jaeger-pf[[:space:]]" > /dev/null
if [ $? -ne 0 ]; then
        screen -dmS jeager-pf bash -c "kubectl config set-context --current --namespace=socialnetwork; kubectl get pods | grep jaeger | awk '{print \$1}' | xargs -I {} kubectl port-forward {} 16686"
fi
sleep 5


kubectl config set-context --current --namespace=socialnetwork
