# locust Alibaba workload
source ../../../.venv/bin/activate

file=$1
wrk_file=$2
chaos_file=$3
home=$PWD

if [[ $# -ne 3 ]]; then
  echo "Usage: $0 <output-csv-name> <workload folder> <chaos_dir>" >&2
  exit 1
fi

cd ../../../locust

screen -dmS locust_cp bash -c "export COMPOSE_CSV=workloads/sin/${wrk_file}/cp_workload.csv; locust --headless --locustfile=locust_compose_post.py --users 1 --spawn-rate 20"
screen -dmS locust_ht bash -c "export HOME_TL_CSV=workloads/sin/${wrk_file}/hts_workload.csv; locust --headless --locustfile=locust_home_tl.py --users 1 --spawn-rate 20"
screen -dmS locust_ut bash -c "export USER_TL_CSV=workloads/sin/${wrk_file}/uts_workload.csv; locust --headless --locustfile=locust_user_tl.py --users 1 --spawn-rate 20"

sleep 5400

cd $home

kubectl apply -f ../$chaos_file

sleep 3600

cd $home

for session in $(screen -ls | grep -o 'locust_[^[:space:]]*'); do
    echo "Terminating screen session: $session"
    screen -S "$session" -X quit
done

python3 ../../../scrape_k8metrics.py 7200s $file
python3 ../../../scrape_traces.py 120 $file

echo $file

kubectl get pods --all-namespaces -o json \
  | jq -r '
      [ "name","namespace","node" ],
      ( .items[]
        | [ .metadata.name, .metadata.namespace, .spec.nodeName ]
      )
      | @csv
    ' > "$HOME/projects/deathstar-data/$file/deployment.csv"

kubectl delete -f ../$chaos_file

cd $home
