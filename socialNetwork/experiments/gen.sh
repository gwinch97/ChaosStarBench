file=$1
wrk=$2
ip=${3:-127.0.0.1}

if [ $wrk -eq 0 ]; then
    url="http://${ip}:8080/wrk2-api/post/compose"
    lua="../wrk2/scripts/social-network/compose-post.lua"
fi
if [ $wrk -eq 1 ]; then
    url="http://${ip}:8080/wrk2-api/user-timeline/read"
    lua="../wrk2/scripts/social-network/read-user-timeline.lua"
fi
if [ $wrk -eq 2 ]; then
    url="http://${ip}:8080/wrk2-api/home-timeline/read"
    lua="../wrk2/scripts/social-network/read-home-timeline.lua"
fi
if [ $wrk -eq 3 ]; then
    url="http://${ip}:8080/wrk2-api"
    lua="../wrk2/scripts/social-network/mixed-workload.lua"
fi

declare -a wrk_array

while IFS=, read -r column1
do
    csv_array+=("$column1")
done < "$file"

for load in "${csv_array[@]}"
do
    echo "Sending ${load} requests to ${url}..."
    screen -dmS wrk-gen bash -c "../../wrk2/wrk -t 20 -c 50 -d 1 -s $lua $url -R ${load}"
    sleep 1
done
