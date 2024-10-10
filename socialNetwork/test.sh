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
