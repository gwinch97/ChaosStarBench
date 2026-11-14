ORIG_DIR="$(pwd)"

echo "CP mem"
# CP mem
for i in 1 2 3; do
  # Tear down and restart
  minikube delete
  cd ../../..
  bash k8startup.sh 2 8000 5 1
  python3 scripts/init_social_graph.py --graph=socfb-Reed98
  cd "$ORIG_DIR"

  wrk_folder="$i"
  bash run_chaos_sin.sh cp_memhog_sin_"$i"_san "$i" memhogchaos/cp_memhog.yaml  
  
done


