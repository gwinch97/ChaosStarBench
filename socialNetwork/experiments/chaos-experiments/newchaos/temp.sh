sleep 4800

python3 ../../../scrape_k8metrics.py 5400s real_workload_test_1
python3 ../../../scrape_traces.py
