source ../../.venv/bin/activate

file=$1
wrk_file=$2
home=$PWD

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <output-csv-name> <workload folder>" >&2
  exit 1
fi

cd ../../locust

screen -dmS locust_cp bash -c "export COMPOSE_CSV=workloads/alibaba/long/S_1823467_workload.csv; locust --headless --locustfile=locust_compose_post.py --users 1 --spawn-rate 5 --run-time 5h"
screen -dmS locust_ht bash -c "export HOME_TL_CSV=workloads/alibaba/long/S_32048416_workload.csv; locust --headless --locustfile=locust_home_tl.py --users 1 --spawn-rate 5 --run-time 5h"
screen -dmS locust_ut bash -c "export USER_TL_CSV=workloads/alibaba/long/S_51794709_workload.csv; locust --headless --locustfile=locust_user_tl.py --users 1 --spawn-rate 5 --run-time 5h"

sleep 21600

cd $home
cd ../chaos-experiments
kubectl apply -f networkchaos/cp_networkdelay.yaml

sleep 7200
kubectl delete -f networkchaos/cp_networkdelay.yaml

#sleep 18000

python3 ../../scrape_k8metrics.py 8 2 $file
python3 ../../scrape_traces.py 8 2 $file

echo $file

kubectl get pods --all-namespaces -o json \
  | jq -r '
      [ "name","namespace","node" ],
      ( .items[]
        | [ .metadata.name, .metadata.namespace, .spec.nodeName ]
      )
      | @csv
    ' > "$HOME/projects/deathstar-data/$file/deployment.csv"

cd $home

