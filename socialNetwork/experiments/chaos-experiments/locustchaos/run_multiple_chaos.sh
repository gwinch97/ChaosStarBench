fn=$1

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <output-csv-name>" >&2
  exit 1
fi

for (( i=i; i<5; i++ )); do
  wrk_folder=$(( i + 5 ))
  bash run_chaos2.sh ${fn}_${i} $wrk_folder
  sleep 600
done
