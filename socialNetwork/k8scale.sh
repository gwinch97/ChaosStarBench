scale=$1
for deploy in $(kubectl get deploy -n socialnetwork -o name); do
         if [[ "$deploy" == *"jaeger"* ]] || [[ "$deploy" == *"mongodb"* ]] || [[ "$deploy" == *"media-frontend"* ]] || [[ "$deploy" == *"nginx"* ]] || [[ "$deploy" == *"redis"* ]] || [[ "$deploy" == *"memcache"* ]]; then
                continue
         fi
         kubectl scale --replicas=$scale $deploy -n socialnetwork;
done
