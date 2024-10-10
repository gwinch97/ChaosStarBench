if kubectl get namespace "socialnetwork" > /dev/null 2>&1; then
	echo "Namespace socialnetwork exists."
else
	kubectl create namespace socialnetwork
	kubectl config set-context --current --namespace=socialnetwork
	cd helm-chart
	helm install v1 socialnetwork-fault
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
