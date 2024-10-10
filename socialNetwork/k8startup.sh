#!/bin/bash
PARTIAL_RUN=false

while getopts ":p" opt; do
	case $opt in
		p)
			PARTIAL_RUN=true
			;;
		\?)
			echo "Invalid option: -$OPTARG" >&2
			exit 1
			;;
	esac
done

if $PARTIAL_RUN; then
	screen -ls | grep "\.kube-tunnel[[:space:]]" > /dev/null
	if [ $? -ne 0 ]; then
		screen -dmS kube-tunnel bash -c "minikube tunnel; exec bash" 
	fi

	screen -ls | grep "\.prom-pf[[:space:]]" > /dev/null
	if [ $? -ne 0 ]; then
		screen -dmS prom-pf bash -c "kubectl config set-context --current --namespace=monitoring; kubectl get pods | grep prometheus-server | awk '{print \$1}' | xargs -I {} kubectl port-forward {} 9090"
	fi

	screen -ls | grep "\.chaos-pf[[:space:]]" > /dev/null
	if [ $? -ne 0 ]; then
		screen -dmS chaos-pf bash -c "helm upgrade chaos-mesh chaos-mesh/chaos-mesh --namespace=chaos-mesh --version 2.6.3 --set dashboard.securityMode=false; kubectl config set-context --current --namespace=chaos-mesh; kubectl get pods | grep chaos-dashboard | awk '{print \$1}' | xargs -I {} kubectl port-forward {} 2333"
	fi

	screen -ls | grep "\.jaeger-pf[[:space:]]" > /dev/null
	if [ $? -ne 0 ]; then
		screen -dmS jaeger-pf bash -c "kubectl config set-context --current --namespace=socialnetwork; kubectl get pods | grep jaeger | awk '{print \$1}' | xargs -I {} kubectl port-forward {} 16686:16686"
		#screen -dmS jaeger-pf bash -c "kubectl port-forward service/jaeger-query 8081:80 -n monitoring"
	fi
	kubectl config set-context --current --namespace=socialnetwork
else
	# Startup minikube cluster
	status=$(minikube status --format='{{.Host}}')
	if [[ "$status" == "Running" ]]; then
		echo "Minikube is already running"
	else
		minikube start --cpus=4 --memory=20000 --extra-config=kubelet.housekeeping-interval=1s --nodes 5
	fi
	# kubectl taint nodes minikube key=monitoring:NoSchedule
	# Fix for persistant volumes permission issue for >1 node clusters (issue#12360)
	minikube addons disable storage-provisioner
	minikube addons disable default-storageclass
	minikube addons enable volumesnapshots
	minikube addons enable csi-hostpath-driver
	kubectl patch storageclass csi-hostpath-sc -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
	
	# Setup deployment
	bash setup-k8.sh

	# Scale socialnetwork deployment
	for deploy in $(kubectl get deploy -n socialnetwork -o name); do
		if [[ "$deploy" == *"jaeger"* ]] || [[ "$deploy" == *"mongodb"* ]] || [[ "$deploy" == *"media-frontend"* ]] || [[ "$deploy" == *"nginx"* ]] || [[ "$deploy" == *"redis"* ]] || [[ "$deploy" == *"memcache"* ]]; then
			continue
		fi
		kubectl scale --replicas=3 $deploy -n socialnetwork;
	done

	# sleep 60

	# Start requried port-forwarding
	pod_running_check() {
		namespace=$1
		pod_name_patter=$2
		kubectl config set-context --curent --namespace=$namespace
		while true; do
			pod_status=$(kubectl get pods --namespace=$namespace | grep $pod_name_pattern | awk '{print $3}')
			if [[ $pod_status == "Running" ]]; then
				break
			fi
			echo "Waiting for pod '$pod_name_pattern' in namespace '$namespace' to be running..."
			sleep 5
		done

	}
	
	screen -ls | grep "\.kube-tunnel[[:space:]]" > /dev/null
	if [ $? -ne 0 ]; then
		screen -dmS kube-tunnel bash -c "minikube tunnel; exec bash" 
	fi
	#sleep 5

	screen -ls | grep "\.prom-pf[[:space:]]" > /dev/null
	if [ $? -ne 0 ]; then
		screen -dmS prom-pf bash -c "./pod_running_check.sh 'monitoring' 'prometheus-server'; kubectl config set-context --current --namespace=monitoring; kubectl get pods | grep prometheus-server | awk '{print \$1}' | xargs -I {} kubectl port-forward {} 9090"
	fi
	#sleep 5

	screen -ls | grep "\.chaos-pf[[:space:]]" > /dev/null
	if [ $? -ne 0 ]; then
		screen -dmS chaos-pf bash -c "./pod_running_check.sh 'chaos-mesh' 'chaos-dashboard'; helm upgrade chaos-mesh chaos-mesh/chaos-mesh --namespace=chaos-mesh --version 2.6.3 --set dashboard.securityMode=false; kubectl config set-context --current --namespace=chaos-mesh; kubectl get pods | grep chaos-dashboard | awk '{print \$1}' | xargs -I {} kubectl port-forward {} 2333"
	fi
	#sleep 5

	screen -ls | grep "\.jaeger-pf[[:space:]]" > /dev/null
	if [ $? -ne 0 ]; then
		screen -dmS jaeger-pf bash -c "./pod_running_check.sh 'socialnetwork' 'jaeger'; kubectl config set-context --current --namespace=socialnetwork; kubectl get pods | grep jaeger | awk '{print \$1}' | xargs -I {} kubectl port-forward {} 16686:16686"
	fi
	#sleep 5

	kubectl config set-context --current --namespace=socialnetwork
fi
#python3 scripts/init_social_graph.py --graph=socfb-Reed98
