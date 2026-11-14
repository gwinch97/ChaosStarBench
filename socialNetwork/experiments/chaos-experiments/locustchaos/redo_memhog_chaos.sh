ORIG_DIR="$(pwd)"

echo "CP mem"
# CP mem
#for i in 0 1 2 3; do
#  # Tear down and restart
#  minikube delete
#  cd ../../..
#  bash k8startup.sh 2 8000 5 1
#  python3 scripts/init_social_graph.py --graph=socfb-Reed98
#  cd "$ORIG_DIR"
#
#  wrk_folder="$i"
#  bash run_chaos_sin.sh cp_memhog_sin_redo_"$i" "$i" memhogchaos/cp_memhog.yaml  
#  
#done

echo "HTS mem"
for i in 2 3; do                                                                                                                                                                           
  # Tear down and restart                                                                                                                                                                      
  minikube delete                                                                                                                                                                              
  cd ../../..                                                                                                                                                                                  
  bash k8startup.sh 2 8000 5 1                                                                                                                                                                 
  python3 scripts/init_social_graph.py --graph=socfb-Reed98                                                                                                                                    
  cd "$ORIG_DIR"                                                                                                                                                                               
                                                                                                                                                                                               
  wrk_folder="$i"                                                                                                                                                                              
  bash run_chaos_sin.sh hts_memhog_redo_sin_"$i" "$i" memhogchaos/hts_memhog.yaml                                                                                                                 
                                                                                                                                                                                                
done 

echo "UTS mem"
for i in 0 1 2 3; do                                                                                                                                                                           
  # Tear down and restart                                                                                                                                                                      
  minikube delete                                                                                                                                                                              
  cd ../../..                                                                                                                                                                                  
  bash k8startup.sh 2 8000 5 1                                                                                                                                                                 
  python3 scripts/init_social_graph.py --graph=socfb-Reed98                                                                                                                                    
  cd "$ORIG_DIR"                                                                                                                                                                               
                                                                                                                                                                                               
  wrk_folder="$i"                                                                                                                                                                              
  bash run_chaos_sin.sh uts_memhog_redo_sin_"$i" "$i" memhogchaos/uts_memhog.yaml                                                                                                                 
                                                                                                                                                                                                
done 

echo "UMS mem"
for i in 0 1 2 3; do                                                                                                                                                                           
  # Tear down and restart                                                                                                                                                                      
  minikube delete                                                                                                                                                                              
  cd ../../..                                                                                                                                                                                  
  bash k8startup.sh 2 8000 5 1                                                                                                                                                                 
  python3 scripts/init_social_graph.py --graph=socfb-Reed98                                                                                                                                    
  cd "$ORIG_DIR"                                                                                                                                                                               
                                                                                                                                                                                               
  wrk_folder="$i"                                                                                                                                                                              
  bash run_chaos_sin.sh ums_memhog_redo_sin_"$i" "$i" memhogchaos/ums_memhog.yaml                                                                                                                 
                                                                                                                                                                                                
done 

