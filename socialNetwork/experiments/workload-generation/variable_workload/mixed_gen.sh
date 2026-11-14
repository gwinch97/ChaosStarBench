file1=$1
file2=$2
file3=$3

screen -dmS cp_wrk bash -c "./gen.sh $file1 0 localhost"
sleep 0.3
screen -dmS ru_wrk bash -c "./gen.sh $file2 1 localhost"
sleep 0.3
screen -dmS rh_wrk bash -c "./gen.sh $file3 2 localhost"
