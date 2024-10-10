T=$1
A=$2
f1=$3
f2=$4
f3=$5
f4=$6
f5=$7
wrk=$8
# Set url and lua script of sin traffic
if [ $wrk -eq 0 ]; then
	url="http://localhost:8080/wrk2-api/post/compose"
	lua="../wrk2/scripts/social-network/compose-post.lua"
fi
if [ $wrk -eq 1 ]; then
	url="http://localhost:8080/wrk2-api/user-timeline/read"
	lua="../wrk2/scripts/social-network/read-user-timeline.lua"
fi
if [ $wrk -eq 2 ]; then
    url="http://localhost:8080/wrk2-api/home-timeline/read"
    lua="../wrk2/scripts/social-network/read-home-timeline.lua"
fi
if [ $wrk -eq 3 ]; then
    url="http://localhost:8080/wrk2-api"
    lua="../wrk2/scripts/social-network/mixed-workload.lua"
fi


calculate_load() {
	local t=$1
	local A=$2
	# Amplitude components
	local A1=$(echo "scale=0; $A*20/100" | bc)
	local A2=$(echo "scale=0; $A*20/100" | bc)
	local A3=$(echo "scale=0; $A*20/100" | bc)
	local A4=$(echo "scale=0; $A*20/100" | bc)
	local A5=$(echo "scale=0; $A*20/100" | bc)
	# Frequency components
	local f1=$3
	local f2=$4
	local f3=$5
	local f4=$6
	local f5=$7

        # Calculate the sum of sine waves 
	# 4*a(1) gives approx of pi
	local sum=$(bc -l <<< "($A1 * s($f1 * $t * 4 * a(1))) + ($A2 * s($f2 * $t * 4 * a(1))) + ($A3 * s($f3 * $t * 4 * a(1))) + ($A4 * s($f4 * $t * 4 * a(1))) + ($A5 * s($f5 * $t * 4 * a(1)))")
	echo $sum
}

offset=$(( ($RANDOM % T) ))
T=$((T + offset))
for (( t=$offset; t<$T; t++ )); do
	load=$(calculate_load $t $A $f1 $f2 $f3 $f4 $f5)
	if [[ $load < 0 ]]; then
		load=$(echo "$load * -1" | bc)
	fi
	load=$(echo "scale=0; ($load / 1) + 20" | bc) # WARNING: DO NOT SET THREAD COUNT HIGHER THAN THE ADDITION IN THIS SUM
	screen -dmS sin-gen bash -c "../../wrk2/wrk -t 20 -c 50 -d 1 -s $lua $url -R $load"
	sleep 1
done


