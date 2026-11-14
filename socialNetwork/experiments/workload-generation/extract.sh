
file=$1

python3 ../../scrape_k8metrics.py 8 2 $file
python3 ../../scrape_traces.py 8 2 $file
