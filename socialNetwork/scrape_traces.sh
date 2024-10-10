#!/bin/bash
fn=$1
T=$2
scrapes=$(((T / 60) + 1))

JAEGER_HOST="localhost"
JAEGER_PORT="16686"
JAEGER_API_ENDPOINT="http://${JAEGER_HOST}:${JAEGER_PORT}/api/traces"
DATA_DIR="/home/gw240/projects/deathstar-data"
OUTPUT_FILE="traces.json"
SERVICE="nginx-web-server"

mkdir -p "/home/gw240/projects/deathstar-data/${fn}"

for i in $(seq 0 $scrapes);
do
	sleep 60
	END_TIME=$(date +%s%3N)
	END_TIME=$(($END_TIME * 1000))
	START_TIME=$(($END_TIME - 70000000))
	echo $END_TIME
	echo $START_TIME
	screen -dmS trace-scrape curl -X GET "${JAEGER_API_ENDPOINT}?service=${SERVICE}&limit=50000&end=${END_TIME}&start=${START_TIME}" -o "/home/gw240/projects/deathstar-data/${fn}/traces_${i}.json"
done
