if kubectl get namespace "socialnetwork" > /dev/null 2>&1; then
	echo "Namespace socialnetwork exists"
else
	echo "Namespace socialnetwork created"
	kubectl create namespace socialnetwork
	kubectl config set-context --current --namespace=socialnetwork
	cd helm-chart
	helm install socialnetwork ./socialnetwork
	echo "----- WAITING FOR JAEGER DEPLOYMENT -----"
	../multiple_pod_running_check.sh socialnetwork socialnetwork-elasticsearch-master
	../multiple_pod_running_check.sh socialnetwork jaeger-collector
	../multiple_pod_running_check.sh socialnetwork jaeger-query
fi

if kubectl get namespace "monitoring" > /dev/null 2>&1; then
	echo "Namespace monitoring exists"
else
	echo "Namespace monitoring created"
	cd ../..
	kubectl create namespace monitoring
	kubectl config set-context --current --namespace=monitoring
	helm install cadvisor ./cadvisor
	helm install prometheus ./prometheus
	kubectl create configmap jaeger-sampling-strategy --from-file=jaeger/sampling-strategy.json
	kubectl config set-context --current --namespace=default
fi

if kubectl get namespace "chaos-mesh" > /dev/null 2>&1; then
    echo "Namespace chaos-mesh exists"
else
	echo "Namespace chaos-mesh created"
	kubectl create namespace chaos-mesh
	kubectl config set-context --current --namespace=chaos-mesh
	helm install chaos-mesh ./chaos-mesh
fi