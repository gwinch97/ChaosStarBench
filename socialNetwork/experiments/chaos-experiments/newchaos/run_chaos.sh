# stabalising workload
cd ../../workload-generation/variable_workload
bash mixed-varying-sin-gen.sh 900 100 0.2 0.4 0.4

sleep 900

bash ../../workload-generation/variable_workload/mixed-varying-sin-gen.sh 5400 100 0.2 0.4 0.4

sleep 3600

cd ../../chaos-experiments/newchaos
kubectl apply -f memhog-chaos/cp_memhog.yaml

sleep 1800

python3 ../../../scrape_k8metrics.py 5400s cp_memory_hog_2
python3 ../../../scrape_traces.py
