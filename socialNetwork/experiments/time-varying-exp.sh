fn=$1
T=$2
A=$3
cp=$3
rh=$4
ru=$5
mkdir -p "/home/gw240/projects/deathstar-data/${fn}"
kubectl get pods -o custom-columns="POD_NAME:.metadata.name,NODE_NAME:.spec.nodeName" | awk 'BEGIN {OFS=","; print "Pod Name,Node"} NR>1 {print $1,$2}' > "/home/gw240/projects/deathstar-data/${fn}/pods_deployment.csv"
# Start experiment
bash mixed-varying-sin-gen.sh $T $A $cp $rh $ru
sleep 1800
#T=$((T + 3600))
#screen -dmS scrape-metrics bash -c "python3 ../scrape_k8metrics.py ${T}s ${fn}"
#screen -dmS scrape-traces bash ../scrape_traces.sh $fn $T
