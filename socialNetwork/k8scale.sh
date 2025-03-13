#!/bin/bash

# 'kubectl top pods' during the wrk2 load generator:
# 
# compose-post-service-xxxxxxxxxx-xxxxx     58m          19Mi            
# home-timeline-redis-xxxxxxxxxx-xxxxx      14m          29Mi            
# home-timeline-service-xxxxxxxxxx-xxxxx    14m          8Mi             
# jaeger-xxxxxxxxxx-xxxxx                   2m           65Mi            
# media-frontend-xxxxxxxxxx-xxxxx           0m           15Mi            
# media-memcached-xxxxxxxxxx-xxxxx          1m           1Mi             
# media-mongodb-xxxxxxxxxx-xxxxx            3m           82Mi            
# media-service-xxxxxxxxxx-xxxxx            4m           1Mi             
# nginx-thrift-xxxxxxxxxx-xxxxx             18m          77Mi            
# post-storage-memcached-xxxxxxxxxx-xxxxx   1m           11Mi            
# post-storage-mongodb-xxxxxxxxxx-xxxxx     15m          114Mi           
# post-storage-service-xxxxxxxxxx-xxxxx     10m          6Mi             
# social-graph-mongodb-xxxxxxxxxx-xxxxx     4m           237Mi           
# social-graph-redis-xxxxxxxxxx-xxxxx       6m           10Mi            
# social-graph-service-xxxxxxxxxx-xxxxx     8m           13Mi            
# text-service-xxxxxxxxxx-xxxxx             27m          2Mi             
# unique-id-service-xxxxxxxxxx-xxxxx        5m           1Mi             
# url-shorten-memcached-xxxxxxxxxx-xxxxx    1m           1Mi             
# url-shorten-mongodb-xxxxxxxxxx-xxxxx      15m          109Mi           
# url-shorten-service-xxxxxxxxxx-xxxxx      14m          2Mi             
# user-memcached-xxxxxxxxxx-xxxxx           9m           3Mi             
# user-mention-service-xxxxxxxxxx-xxxxx     14m          2Mi             
# user-mongodb-xxxxxxxxxx-xxxxx             4m           108Mi           
# user-service-xxxxxxxxxx-xxxxx             4m           8Mi             
# user-timeline-mongodb-xxxxxxxxxx-xxxxx    18m          100Mi           
# user-timeline-redis-xxxxxxxxxx-xxxxx      5m           5Mi             
# user-timeline-service-xxxxxxxxxx-xxxxx    12m          2Mi
#
# for simplicity, focus on scaling up these pods first

output=$(kubectl top node)

if [ "$output" = "error: Metrics API not available" ]; then
    echo "$output"
    echo "Have you added: '--kubelet-insecure-tls=true'"
    echo "Usually completed through running the 'k8startup.sh' script."
else
    # the autoscaler can begin
    kubectl config set-context --current --namespace=socialnetwork
    kubectl autoscale deployment compose-post-service --cpu-percent=50 --min=1 --max=3
    kubectl autoscale deployment home-timeline-service --cpu-percent=50 --min=1 --max=2
    kubectl autoscale deployment media-service --cpu-percent=50 --min=1 --max=2
    kubectl autoscale deployment post-storage-service --cpu-percent=50 --min=1 --max=2
    kubectl autoscale deployment social-graph-service --cpu-percent=50 --min=1 --max=2
    kubectl autoscale deployment text-service --cpu-percent=50 --min=1 --max=2
    kubectl autoscale deployment unique-id-service --cpu-percent=50 --min=1 --max=2
    kubectl autoscale deployment url-shorten-service --cpu-percent=50 --min=1 --max=2
    kubectl autoscale deployment user-mention-service --cpu-percent=50 --min=1 --max=2
    kubectl autoscale deployment user-service --cpu-percent=50 --min=1 --max=2
    kubectl autoscale deployment user-timeline-service --cpu-percent=50 --min=1 --max=2
fi

# run 'kubectl get hpa' for min, max and replicas
# run 'kubectl get hpa {service-name} --watch' to see realtime usage