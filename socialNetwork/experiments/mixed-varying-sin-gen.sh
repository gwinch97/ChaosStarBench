T=$1
A=$2
cp=$3
rh=$4
ru=$5

generate_random_decimal() {
	local average=$1
	local range=$2
	awk -v avg="$average" -v seed="$RANDOM" -v rng="$range" 'BEGIN{
	srand(seed);
	print avg - rng + (rand() * (2 * rng))}'
}

create_linear_array() {
  local start_value=$1
  local end_value=$2
  local N=$3
  local delta=$(bc -l <<< "($end_value - $start_value)/($N-1)")

  local array_str=""  # Initialize an empty string

  for ((i=0; i<N; i++)); do
    local value=$(bc -l <<< "$start_value + $i * $delta")
    array_str+=$(printf "%.3f " "$value")  # Add each calculated value to the string
  done

  echo "$array_str"  # Echo the string containing all array elements
}

# Generate time-varying arrays
Arh_arr_str=$(create_linear_array 1 0 $T)
read -r -a Arh_arr <<< "$Arh_arr_str"
Arh_str=$(IFS=,; echo "${Arh_arr[*]}")

Acp_arr_str=$(create_linear_array 0 1 $T)
read -r -a Acp_arr <<< "$Acp_arr_str"
Acp_str=$(IFS=,; echo "${Acp_arr[*]}")

# Read home timeline
if (( $(echo "$rh > 0" | bc -l) )); then
	# generate random frequency components
	# Average 1hr period
	f1=$(awk -v min=0.01 -v max=0.02 'BEGIN{srand(); print min+rand()*(max-min)}')
	# Average 30m period
	f2=$(awk -v min=0.02 -v max=0.03 'BEGIN{srand(); print min+rand()*(max-min)}')
	f3=$(awk -v min=0.03 -v max=0.04 'BEGIN{srand(); print min+rand()*(max-min)}')
	# Average 5m period
	f4=$(awk -v min=0.04 -v max=0.05 'BEGIN{srand(); print min+rand()*(max-min)}')
	f5=$(awk -v min=0.05 -v max=0.06 'BEGIN{srand(); print min+rand()*(max-min)}')
	screen -dmS rh-wrk bash -c "bash tv-sin-gen.sh $T $A $Arh_str $f1 $f2 $f3 $f4 $f5 2"
fi

# Compose post
if (( $(echo "$cp > 0" | bc -l) )); then
	# generate random frequency components
	# Average 1hr period
	f1=$(awk -v min=0.01 -v max=0.02 'BEGIN{srand(); print min+rand()*(max-min)}')
	# Average 30m period
	f2=$(awk -v min=0.02 -v max=0.03 'BEGIN{srand(); print min+rand()*(max-min)}')
	f3=$(awk -v min=0.03 -v max=0.04 'BEGIN{srand(); print min+rand()*(max-min)}')
	# Average 5m period
	f4=$(awk -v min=0.04 -v max=0.05 'BEGIN{srand(); print min+rand()*(max-min)}')
	f5=$(awk -v min=0.05 -v max=0.06 'BEGIN{srand(); print min+rand()*(max-min)}')
	screen -dmS cp-wrk bash -c "bash tv-sin-gen.sh $T $A $Acp_str $f1 $f2 $f3 $f4 $f5 0"
fi

# Read user timeline
if (( $(echo "$cp > 0" | bc -l) )); then
        # generate random frequency components
        # Average 1hr period
        f1=$(awk -v min=0.01 -v max=0.02 'BEGIN{srand(); print min+rand()*(max-min)}')
        # Average 30m period
        f2=$(awk -v min=0.02 -v max=0.03 'BEGIN{srand(); print min+rand()*(max-min)}')
        f3=$(awk -v min=0.03 -v max=0.04 'BEGIN{srand(); print min+rand()*(max-min)}')
        # Average 5m period
        f4=$(awk -v min=0.04 -v max=0.05 'BEGIN{srand(); print min+rand()*(max-min)}')
        f5=$(awk -v min=0.05 -v max=0.06 'BEGIN{srand(); print min+rand()*(max-min)}')
        screen -dmS ru-wrk bash -c "bash tv-sin-gen.sh $T $A $Acp_str $f1 $f2 $f3 $f4 $f5 1"
fi
