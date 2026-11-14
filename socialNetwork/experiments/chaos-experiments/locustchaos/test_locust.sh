source ../../../.venv/bin/activate

file=$1
wrk_file=$2
home=$PWD

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <output-csv-name> <workload folder>" >&2
  exit 1
fi

#cd ../../../locust

#screen -dmS locust_cp bash -c "export COMPOSE_CSV=workloads/S_1823467_workload.csv; locust --headless --locustfile=locust_compose_post.py --
#users 1 --spawn-rate 5"


cd ../../workload-generation/variable_workload

screen -dmS wrk2_gen bash -c "./wrk_test.sh ali_workloads/S_1823467_workload.csv 0"

sleep 600

cd $home

for session in $(screen -ls | grep -o 'wrk2_[^[:space:]]*'); do
    echo "Terminating screen session: $session"
    screen -S "$session" -X quit
done

python3 ../../../scrape_k8metrics.py 600s $file
python3 ../../../scrape_traces.py 10 $file
