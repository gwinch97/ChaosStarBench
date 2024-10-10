T=$1
A=$2
A_arr_str=$3
f1=$4
f2=$5
f3=$6
f4=$7
f5=$8
wrk=$9
# Set url and lua script of sin traffic
if [ $wrk -eq "0" ]; then
	url="http://localhost:8080/wrk2-api/post/compose"
	lua="../wrk2/scripts/social-network/compose-post.lua"
fi
if [ $wrk -eq "1" ]; then
	url="http://localhost:8080/wrk2-api/user-timeline/read"
	lua="../wrk2/scripts/social-network/read-user-timeline.lua"
fi
if [ $wrk -eq "2" ]; then
    url="http://localhost:8080/wrk2-api/home-timeline/read"
    lua="../wrk2/scripts/social-network/read-home-timeline.lua"
fi
if [ $wrk -eq "3" ]; then
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
	# NOTE: 4*a(1) gives approx of pi
	local sum=$(bc -l <<< "($A1 * s($f1 * $t * 4 * a(1))) + ($A2 * s($f2 * $t * 4 * a(1))) + ($A3 * s($f3 * $t * 4 * a(1))) + ($A4 * s($f4 * $t * 4 * a(1))) + ($A5 * s($f5 * $t * 4 * a(1)))")
	echo $sum
}

IFS=',' read -r -a A_arr <<< "$A_arr_str"

# For the first hour keep the initial state, 1800s of equilibrium 1800s of init data
T_eq=3600
offset=$(( ($RANDOM % T_eq) ))
T_eq=$((T_eq + offset))
for (( t=$offset; t<$T_eq; t++ )); do
	A_adj=$(echo "scale=0; $A * ${A_arr[1]}" | bc)
	A_adj=$(echo "scale=0; $A_adj / 1" | bc)
	load=$(calculate_load $t $A_adj $f1 $f2 $f3 $f4 $f5)
	if (( $(echo "$load < 0" | bc -l) )); then
		load=$(echo "$load * -1" | bc)
	fi
	load=$(echo "scale=0; ($load / 1) + 10" | bc) # WARNING: DO NOT SET THREAD COUNT HIGHER THAN THE ADDITION IN THIS SUM
	screen -dmS sin-gen bash -c "../../wrk2/wrk -t 10 -c 25 -d 1 -s $lua $url -R $load"
	sleep 1
done


# Time-varying traffic
offset=$((offset + T_eq))
T=$((T + offset))
i=1
for (( t=$offset; t<$T; t++ )); do
	A_adj=$(echo "scale=0; $A * ${A_arr[$i]}" | bc)
	A_adj=$(echo "scale=0; $A_adj / 1" | bc)
	load=$(calculate_load $t $A_adj $f1 $f2 $f3 $f4 $f5)
	if [[ $load < 0 ]]; then
		load=$(echo "$load * -1" | bc)
	fi
	load=$(echo "scale=0; ($load / 1) + 10" | bc) # WARNING: DO NOT SET THREAD COUNT HIGHER THAN THE ADDITION IN THIS SUM
	screen -dmS sin-gen bash -c "../../wrk2/wrk -t 10 -c 25 -d 1 -s $lua $url -R $load"
	sleep 1
	i=$((i + 1))
done

# Magnitude-varying traffic
offset=$((offset + T))
T=$((3600 + offset))
j=0.1
for (( t=$offset; t<$T; t++ )); do
	A_adj=$(echo "scale=0; $A * ${A_arr[$i]} + $j" | bc)
	A_adj=$(echo "scale=0; $A_adj / 1" | bc)
	load=$(calculate_load $t $A_adj $f1 $f2 $f3 $f4 $f5)
	if [[ $load < 0 ]]; then
		load=$(echo "$load * -1" | bc)
	fi
	load=$(echo "scale=0; ($load / 1) + 10" | bc) # WARNING: DO NOT SET THREAD COUNT HIGHER THAN THE ADDITION IN THIS SUM
	screen -dmS sin-gen bash -c "../../wrk2/wrk -t 10 -c 25 -d 1 -s $lua $url -R $load"
	sleep 1
	j=$(echo "$j + 0.1" | bc)
done


