#!/bin/bash
# Start a fresh minikube cluster with hotelReservation, Prometheus and Chaos Mesh.
# Adapted from socialNetwork/k8startup.sh (same cluster shape, kubelet housekeeping 1s,
# CSI hostpath storage, local PV for Prometheus, chaosd on the nodes).
# Usage: k8startup_hotel.sh [values-fcadl.yaml|values-memlimit.yaml]
set -euo pipefail
cd "$(dirname "$0")"
source ./config.sh
VALUES=${1:-values-fcadl.yaml}

echo "----- START MINIKUBE -----"
if [ "$(minikube status --format='{{.Host}}' 2>/dev/null || true)" != "Running" ]; then
  minikube start --kubernetes-version=v1.28.6 --driver=docker \
    --cpus="$NODE_CPUS" --memory="$NODE_MEM_MB" --nodes="$N_NODES" \
    --extra-config=kubelet.housekeeping-interval=1s --extra-config=kubelet.fail-swap-on=false
fi
kubectl taint node minikube node-role.kubernetes.io/control-plane=:NoSchedule --overwrite || true

echo "----- STORAGE (as socialNetwork/k8startup.sh) -----"
minikube addons disable storage-provisioner || true
minikube addons disable default-storageclass || true
minikube addons enable volumesnapshots
minikube addons enable csi-hostpath-driver
kubectl delete storageclass csi-hostpath-sc --ignore-not-found
cat <<YAML | kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: csi-hostpath-sc
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"
provisioner: hostpath.csi.k8s.io
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Delete
allowVolumeExpansion: true
YAML
minikube ssh -- "sudo mkdir -p /data/prometheus && sudo chown docker:docker /data/prometheus"
cat <<YAML | kubectl apply -f -
apiVersion: v1
kind: PersistentVolume
metadata:
  name: prometheus-minikube-local-pv
spec:
  capacity:
    storage: 24Gi
  accessModes: [ReadWriteOnce]
  persistentVolumeReclaimPolicy: Delete
  storageClassName: csi-hostpath-sc
  volumeMode: Filesystem
  local:
    path: /data/prometheus
  nodeAffinity:
    required:
      nodeSelectorTerms:
        - matchExpressions:
            - {key: kubernetes.io/hostname, operator: In, values: [minikube]}
YAML

echo "----- HOTEL RESERVATION ($VALUES) -----"
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
helm upgrade --install "$RELEASE" "$CHART" -n "$NAMESPACE" -f "$VALUES"

echo "----- PROMETHEUS -----"
kubectl create namespace prometheus --dry-run=client -o yaml | kubectl apply -f -
helm upgrade --install prometheus ../prometheus -n prometheus

echo "----- CHAOS MESH -----"
kubectl create namespace chaos-mesh --dry-run=client -o yaml | kubectl apply -f -
helm upgrade --install chaos-mesh ../chaos-mesh -n chaos-mesh --set dashboard.securityMode=false
for node in $(minikube node list | awk '{print $1}'); do
  minikube cp ../socialNetwork/k8install_chaosd.sh "$node":/home/docker/k8install_chaosd.sh
  minikube ssh -n "$node" -- "bash ./k8install_chaosd.sh" || true
done

echo "----- WAIT FOR PODS -----"
kubectl wait --for=condition=Ready pods --all -n "$NAMESPACE" --timeout=900s
kubectl wait --for=condition=Ready pods --all -n prometheus --timeout=900s
kubectl wait --for=condition=Ready pods --all -n chaos-mesh --timeout=900s

echo "----- PORT FORWARDS (frontend :$FRONTEND_PORT, prometheus :$PROM_PORT) -----"
pkill -f "port-forward.*frontend-$RELEASE" || true
pkill -f "port-forward.*prometheus-server" || true
nohup kubectl port-forward -n "$NAMESPACE" "svc/frontend-$RELEASE" "$FRONTEND_PORT:5000" >/tmp/pf-frontend.log 2>&1 &
nohup kubectl port-forward -n prometheus svc/prometheus-server "$PROM_PORT:80" >/tmp/pf-prom.log 2>&1 &
sleep 5
curl -sf "http://localhost:$FRONTEND_PORT/hotels?inDate=2015-04-09&outDate=2015-04-10&lat=38.0235&lon=-122.095" >/dev/null \
  && echo "frontend OK" || { echo "frontend not answering"; exit 1; }
curl -sf "http://localhost:$PROM_PORT/api/v1/query?query=up" >/dev/null \
  && echo "prometheus OK" || { echo "prometheus not answering"; exit 1; }
