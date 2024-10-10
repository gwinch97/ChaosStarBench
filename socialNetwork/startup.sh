sudo docker-compose down
sudo docker-compose up -d
python3 scripts/init_social_graph.py --graph=socfb-Reed98

# Add NET to user mention
sudo docker exec socialnetwork_user-mention-service_1 apt update
sudo docker exec socialnetwork_user-mention-service_1 apt install libatm1 libmnl0 libxtables11 iproute2
sudo docker exec socialnetwork_user-mention-service_1 tc qdisc add dev eth0 root netem delay 100ms
sudo docker exec socialnetwork_user-mention-service_1 tc qdisc del dev eth0 root

# Add NET to post storage
sudo docker exec socialnetwork_post-storage-service_1 apt update
sudo docker exec socialnetwork_post-storage-service_1 apt install libatm1 libmnl0 libxtables11 iproute2
sudo docker exec socialnetwork_post-storage-service_1 tc qdisc add dev eth0 root netem delay 100ms
sudo docker exec socialnetwork_post-storage-service_1 tc qdisc del dev eth0 root
