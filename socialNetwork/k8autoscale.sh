#!/bin/bash

# top pods during the wrk2 workload generator are:
# 
# compose-post-service-54d5f7f8f7-w259b     58m          19Mi            
# home-timeline-redis-5cdbd67f7c-xvzh6      14m          29Mi            
# home-timeline-service-846989fcd5-bb565    14m          8Mi             
# jaeger-79c8c846c8-xm5fx                   2m           65Mi            
# media-frontend-6bbbb8648f-w5gl9           0m           15Mi            
# media-memcached-8bdff88f6-rz2t6           1m           1Mi             
# media-mongodb-85f4f7f55-wclkr             3m           82Mi            
# media-service-bb9d6c8d6-wzlm8             4m           1Mi             
# nginx-thrift-fb56689d4-ncpbz              18m          77Mi            
# post-storage-memcached-55dcdfffbd-b9h7b   1m           11Mi            
# post-storage-mongodb-5bf878564c-745df     15m          114Mi           
# post-storage-service-76b64fb6dc-rm4ls     10m          6Mi             
# social-graph-mongodb-596cdcf88c-9c9vj     4m           237Mi           
# social-graph-redis-69c658d694-6wrns       6m           10Mi            
# social-graph-service-79c848748f-lnb46     8m           13Mi            
# text-service-6745755f75-9wwhp             27m          2Mi             
# unique-id-service-5578bf47d8-4s5n9        5m           1Mi             
# url-shorten-memcached-64c6c7557d-cqnpm    1m           1Mi             
# url-shorten-mongodb-ccd7bb58d-7568t       15m          109Mi           
# url-shorten-service-c85b5c7f6-4558b       14m          2Mi             
# user-memcached-59967f9b78-jhkxq           9m           3Mi             
# user-mention-service-d8cbd6fcf-k9jvd      14m          2Mi             
# user-mongodb-6c75c9d7db-wx7kj             4m           108Mi           
# user-service-559b79c875-tcvn9             4m           8Mi             
# user-timeline-mongodb-6ccb4447d8-n8grv    18m          100Mi           
# user-timeline-redis-546bbd644f-6whkb      5m           5Mi             
# user-timeline-service-577586758f-t4kgb    12m          2Mi
#
# for simplicity, focus on scaling up these pods first

output=$(kubectl top node)

if [ "$output" = "error: Metrics API not available" ]; then
    echo "Metrics server cannot run..."
    echo "Have you tried adding: '--kubelet-insecure-tls=true'"
    echo "To the command: 'kubectl edit deploy metrics-server -n kube-system'?"
else
    # the autoscaler can begin
    kubectl autoscale deployment compose-post-service --cpu-percent=50 --min=1 --max=3
    kubectl autoscale deployment home-timeline-redis --cpu-percent=50 --min=1 --max=2
    kubectl autoscale deployment home-timeline-service --cpu-percent=50 --min=1 --max=2
    kubectl autoscale deployment nginx-thrift --cpu-percent=50 --min=1 --max=2
    kubectl autoscale deployment post-storage-mongodb --cpu-percent=50 --min=1 --max=2
    kubectl autoscale deployment post-storage-service --cpu-percent=50 --min=1 --max=2
    kubectl autoscale deployment text-service --cpu-percent=50 --min=1 --max=2
    kubectl autoscale deployment url-shorten-mongodb --cpu-percent=50 --min=1 --max=2
    kubectl autoscale deployment url-shorten-service --cpu-percent=50 --min=1 --max=2
    kubectl autoscale deployment user-mention-service --cpu-percent=50 --min=1 --max=2
    kubectl autoscale deployment user-timeline-mongodb --cpu-percent=50 --min=1 --max=2
    kubectl autoscale deployment user-timeline-service --cpu-percent=50 --min=1 --max=2
fi

# run kubectl get hpa for min, max and replicas
# run kubectl get hpa {service-name} --watch to see realtime usage