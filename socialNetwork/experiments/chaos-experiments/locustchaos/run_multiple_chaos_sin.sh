echo "CP cpu"
# CP cpu
#for (( i=2; i<4; i++ )); do
#  wrk_folder=$(( i + 5 ))
#  bash run_chaos_sin.sh cp_cpuhog_sin${i} ${i} cpuhogchaos/cp_cpuhog.yaml
#  sleep 600
#done

echo "CP mem"
# CP mem
#for (( i=2; i<4; i++ )); do
#	wrk_folder=${i}
#	bash run_chaos_sin.sh cp_memhog_sin_${i} ${i} memhogchaos/cp_memhog.yaml
#	sleep 600
#done

echo "HTS cpu"
# HTS cpu
#for (( i=2; i<4; i++ )); do
#        wrk_folder=${i}
#        bash run_chaos_sin.sh hts_cpuhog_sin_${i} ${i} cpuhogchaos/hts_cpuhog.yaml
#	sleep 600
#done

echo "HTS mem"
# HTS mem
#for (( i=2; i<4; i++ )); do
#        wrk_folder=${i}
#        bash run_chaos_sin.sh hts_memhog_sin_${i} ${i} memhogchaos/hts_memhog.yaml
#        sleep 600
#done

echo "CP net"
# CP net
#for (( i=2; i<4; i++ )); do
#        wrk_folder=${i}
#        bash run_chaos_sin.sh cp_networkdelay_sin_${i} ${i} networkchaos/cp_networkdelay.yaml
#        sleep 600
#done

echo "HTS net"
# HTS net
#for (( i=3; i<4; i++ )); do
#        wrk_folder=${i}
#        bash run_chaos_sin.sh hts_netdelay_sin_${i} ${i} networkchaos/hts_networkdelay.yaml
#	sleep 600
#done

echo "UTS cpu"
# UMS cpu
#for (( i=1; i<4; i++ )); do
#        wrk_folder=${i}
#        bash run_chaos_sin.sh ums_cpuhog_sin_${i} ${i} cpuhogchaos/ums_cpuhog.yaml
#	sleep 600
#done

echo "UTS mem"
# UMS mem
#for (( i=0; i<4; i++ )); do
#        wrk_folder=${i}
#        bash run_chaos_sin.sh ums_memhog_sin_${i} ${i} memhogchaos/ums_memhog.yaml
#        sleep 600
#done

echo "UTS net"
# UMS net
#for (( i=0; i<4; i++ )); do
#        wrk_folder=${i}
#        bash run_chaos_sin.sh ums_netdelay_sin_${i} ${i} networkchaos/ums_networkdelay.yaml
#        sleep 600
#done

echo "UTS cpu"
# UMS cpu
#for (( i=1; i<4; i++ )); do
#        wrk_folder=${i}
#        bash run_chaos_sin.sh uts_cpuhog_sin_${i} ${i} cpuhogchaos/uts_cpuhog.yaml
#        sleep 600
#done

echo "UTS mem"
# UMS mem
#for (( i=3; i<4; i++ )); do
#        wrk_folder=${i}
#        bash run_chaos_sin.sh uts_memhog_sin_${i} ${i} memhogchaos/uts_memhog.yaml
#        sleep 600
#done

echo "UTS net"
# UMS net
for (( i=3; i<4; i++ )); do
        wrk_folder=${i}
        bash run_chaos_sin.sh uts_netdelay_sin_${i} ${i} networkchaos/uts_networkdelay.yaml
        sleep 600
done


bash run_chaos_sin.sh uts_cpuhog_sin_0 0 cpuhogchaos/uts_cpuhog.yaml
sleep 600

bash run_chaos_sin.sh uts_cpuhog_sin_3 3 cpuhogchaos/uts_cpuhog.yaml
sleep 600





