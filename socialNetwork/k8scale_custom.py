"""This file runs an autoscaling algorithm for the Social Network Kubernetes deployment"""

# Uses some equations from 'Practical Efficient Microservice Autoscaling' (Md Rajib Hossen, Mohammad A. Islam)

import os
import threading
import time

import requests
from kubernetes import client, config
from kubernetes.client import ApiException
from elasticsearch import Elasticsearch, helpers

# GET DEPLOYMENT IP AND PORTS
IP_ADDRESS = "127.0.0.1"
ELASTICSEARCH_PORT = 9200
JAEGER_PORT = 16686
PROM_PORT = 9090

# QUERY SPECIFIC VARIABLES
# rate(container_cpu_usage_seconds_total{namespace=~"socialnetwork", pod=~".*service.*"}[1m])
# rate(container_cpu_cfs_throttled_seconds_total{namespace=~"socialnetwork", pod=~".*service.*"}[1m])
OUTPUT_FILE = "temp.json"
PROM_CPU_UTILISATION = f"http://{IP_ADDRESS}:{PROM_PORT}/api/v1/query?query=container_cpu_usage_seconds_total{{namespace='socialnetwork', pod=~'.*service.*'}}[1m]"
PROM_CPU_THROTTLING = f"http://{IP_ADDRESS}:{PROM_PORT}/api/v1/query?query=container_cpu_cfs_throttled_seconds_total{{namespace='socialnetwork', pod=~'.*service.*'}}[1m]"

# SCALING SPECIFIC SETTINGS
SCALE_DOWN_THRESHOLD_RESPONSE_TIME = 300 # response time in microseconds when scaling down is needed
SCALE_DOWN_THRESHOLD_UTILISATION = 45.0  # cpu utilisation % when scaling down is needed
SCALE_DOWN_THRESHOLD_THROTTLING = 2.5  # cpu throttle % when scaling down is needed
SCALE_DOWN_GRACE_PERIOD = 15  # time in seconds between first meeting the threshold and then scaling down
SCALE_UP_THRESHOLD_RESPONSE_TIME = 1000 # response time in microseconds when scaling up is needed
SCALE_UP_THRESHOLD_UTILISATION = 85.0  # cpu utilisation % when scaling up is needed
SCALE_UP_THRESHOLD_THROTTLING = 10.0  # cpu throttling % when scaling up is needed
SCALE_UP_GRACE_PERIOD = 5  # time in seconds between first meeting the threshold and then scaling up
AFTER_GRACE_PERIOD = 15  # time in seconds after scaling to wait before scaling again
MINIMUM_INSTANCES = 1  # min amount of instances of each service
MAXIMUM_INSTANCES = 5  # max amount of instances of each service

# KUBERNETES APIS
config.load_kube_config()
core_api = client.CoreV1Api()
apps_api = client.AppsV1Api()
autoscale_api = client.AutoscalingV1Api()

# LIST OF RUNNING THREADS
running_threads = []

# DICTIONARY OF SERVICE INFORMATION
services = {
    "post-storage-service": {"response_time": [0], "cpu_utilisation": [0.0], "cpu_throttling": [0.0], "instances": 0},
    "user-mention-service": {"response_time": [0], "cpu_utilisation": [0.0], "cpu_throttling": [0.0], "instances": 0},
    "user-service": {"response_time": [0], "cpu_utilisation": [0.0], "cpu_throttling": [0.0], "instances": 0},
    "unique-id-service": {"response_time": [0], "cpu_utilisation": [0.0], "cpu_throttling": [0.0], "instances": 0},
    "media-service": {"response_time": [0], "cpu_utilisation": [0.0], "cpu_throttling": [0.0], "instances": 0},
    "social-graph-service": {"response_time": [0], "cpu_utilisation": [0.0], "cpu_throttling": [0.0], "instances": 0},
    "url-shorten-service": {"response_time": [0], "cpu_utilisation": [0.0], "cpu_throttling": [0.0], "instances": 0},
    "compose-post-service": {"response_time": [0], "cpu_utilisation": [0.0], "cpu_throttling": [0.0], "instances": 0},
    "user-timeline-service": {"response_time": [0], "cpu_utilisation": [0.0], "cpu_throttling": [0.0], "instances": 0},
    "home-timeline-service": {"response_time": [0], "cpu_utilisation": [0.0], "cpu_throttling": [0.0], "instances": 0},
    "text-service": {"response_time": [0], "cpu_utilisation": [0.0], "cpu_throttling": [0.0], "instances": 0}}


def main():
    """Running Autoscaling Script"""

    # disable HPA to ensure you can scale with custom metrics
    disable_hpa("socialnetwork")

    # get current number of instances of all services in the namespace
    get_replicas("socialnetwork")

    # ready to begin gathering data and scaling up
    autoscale()


def remove_hex_code(pod_name):
    """Takes the name of a pod, like 'compose-post-service-12fd5', and returns 'compose-post-service'"""
    return "-".join(pod_name.split("-")[:-2])


def add_to_list(item, existing_list):
    """Takes the existing list of services and appends the new metric at the beginning"""
    new_list = [item] + existing_list[:11] # first 11 items in old list
    # this list contains 12 items, and each item is 1 timestep
    # therefore this list is the previous 120 seconds of performance metrics
    return new_list


def disable_hpa(namespace):
    """Attempts to disable any other algorithms that may conflict with this application"""
    try:
        pods = core_api.list_namespaced_pod(namespace=namespace).items

        for pod in pods:
            # extract name of pod without the hex code at the end
            resource_name = remove_hex_code(pod.metadata.name)

            try:
                # disable HPA for every service to ensure there are no conflicts with this script
                autoscale_api.delete_namespaced_horizontal_pod_autoscaler(name=resource_name, namespace=namespace, )
            except ApiException:
                pass

    except Exception as e:
        print(f"Unexpected Exception: {e}")


def get_replicas(namespace):
    """Attempts to get the amount of replicas for each pod"""
    try:
        for microservice_name in services.keys():
            try:
                # get current number of replicas
                deployment = apps_api.read_namespaced_deployment(name=microservice_name, namespace=namespace)
                services[microservice_name]['instances'] = deployment.spec.replicas
            except ApiException:
                pass

    except Exception as e:
        print(e)


def autoscale():
    """Runs the autoscale algorithm on a loop"""
    try:
        # Initialize Elasticsearch
        es = Elasticsearch([{'host': IP_ADDRESS, 'port': ELASTICSEARCH_PORT, 'scheme': 'http'}])
        index_pattern = "jaeger-span-*"
        scroll = '2m'
        batch_size = 500

        while True:
            # GET JAEGER TRACE LATENCY
            # Get epoch time 15 seconds ago (in milliseconds)
            epoch_time_10s_ago = int(time.time() - 10) * 1000

            # Initialize the query to match traces based on the startTimeMillis field
            query = {"_source": ["process.serviceName", "duration"],
                     "query": {"range": {"startTimeMillis": {"gte": epoch_time_10s_ago}}}}

            try:
                total = es.count(index=index_pattern, body={"query": query['query']})['count']
            except Exception:
                print("Unable to query Jaeger response time")
                total = 0

            if total != 0:
                scroll_gen = helpers.scan(client=es, index=index_pattern, query=query, scroll=scroll, size=batch_size,
                                          preserve_order=False)

                for doc in scroll_gen:
                    trace = doc['_source']
                    service_name = trace['process']['serviceName']
                    duration_microseconds = trace['duration']
                    services[service_name]['response_time'] = add_to_list(duration_microseconds, services[service_name]['response_time'])

            # GET PROMETHEUS CPU USAGE
            try:
                response = requests.get(url=PROM_CPU_UTILISATION, timeout=10)
                metrics = response.json()["data"]["result"]
            except Exception:
                print("Unable to query Prometheus CPU utilisation")
                metrics = []
            
            for metric in metrics:
                service_name = remove_hex_code(metric["metric"]["pod"])  # pod name
                values = metric["values"]  # pod usage as [timestamp, value]
                cpu_usage = float(values[-1][1])  # get most recent value
                services[service_name]['cpu_utilisation'] = add_to_list(cpu_usage, services[service_name]['cpu_utilisation'])

            # GET PROMETHEUS CPU THROTTLING
            try:
                response = requests.get(url=PROM_CPU_THROTTLING, timeout=10)
                metrics = response.json()["data"]["result"]
            except Exception:
                print("Unable to query Prometheus CPU throttling")
                metrics = []

            for metric in metrics:
                service_name = remove_hex_code(metric["metric"]["pod"])  # pod name
                values = metric["values"]  # pod throttling as [timestamp, value]
                cpu_throttling = float(values[-1][1])  # get most recent value
                services[service_name]['cpu_throttling'] = add_to_list(cpu_throttling, services[service_name]['cpu_throttling'])

            print("---------------------------------------------------------------------")
            print("SERVICE NAME               | UTILISATION | THROTTLING | RESPONSE TIME")
            print("---------------------------------------------------------------------")

            for service_name, service_data in services.items():
                instances = service_data["instances"]
                cpu_util = float(service_data['cpu_utilisation'][0])
                cpu_throttling = float(service_data['cpu_throttling'][0])
                response_time = service_data["response_time"][0]

                # print the data into the table
                print(f"{service_name:<{21}} ({instances}x) "
                      f"| {f'{cpu_util:.2f}%':<{12}}"
                      f"| {f'{cpu_throttling:.2f}%':<{11}}"
                      f"| {f'{response_time}µs':<{16}}")

                # check if you need to scale the service
                # based on whether you are allowed to add or remove instances
                # and whether they are already attempting to scale
                if service_data['instances'] < MAXIMUM_INSTANCES and service_name not in running_threads:
                    should_scale_up = (response_time > SCALE_UP_THRESHOLD_RESPONSE_TIME 
                                       or cpu_util > SCALE_UP_THRESHOLD_UTILISATION 
                                       or cpu_throttling > SCALE_UP_THRESHOLD_THROTTLING)

                    if should_scale_up:
                        thread = threading.Thread(target=scale_up, args=(service_name,), name=f"{service_name}")
                        running_threads.append(f"{service_name}")
                        thread.start()
                elif service_data['instances'] > MINIMUM_INSTANCES and service_name not in running_threads:
                    should_scale_down = (response_time < SCALE_DOWN_THRESHOLD_RESPONSE_TIME 
                                         and cpu_util < SCALE_DOWN_THRESHOLD_UTILISATION 
                                         and cpu_throttling < SCALE_DOWN_THRESHOLD_THROTTLING)

                    if should_scale_down:
                        reduction = (service_data['instances'] - 1) * min((SCALE_DOWN_THRESHOLD_RESPONSE_TIME - service_data['response_time']) / SCALE_DOWN_THRESHOLD_RESPONSE_TIME, 1)
                        thread = threading.Thread(target=scale_down, args=(service_name,reduction,), name=f"{service_name}")
                        running_threads.append(f"{service_name}")
                        thread.start()

            # stop for a few seconds before running again
            time.sleep(10)
    except KeyboardInterrupt:
        # wait for open threads
        for thread in threading.enumerate():
            if thread != threading.main_thread():
                thread.join()

        # delete any temp files
        if os.path.isfile(OUTPUT_FILE):
            os.remove(OUTPUT_FILE)

        exit()


def scale_up(service_name):
    """Scales up the given service"""
    time.sleep(SCALE_UP_GRACE_PERIOD)  # check after grace period before scaling

    response_time = services[service_name]['response_time'][0]
    cpu_util = float(services[service_name]['cpu_utilisation'][0])
    cpu_throttling = float(services[service_name]['cpu_throttling'][0])

    still_exceeding_threshold = (response_time > SCALE_UP_THRESHOLD_RESPONSE_TIME 
                                 or cpu_util > SCALE_UP_THRESHOLD_UTILISATION 
                                 or cpu_throttling > SCALE_UP_THRESHOLD_THROTTLING)

    if still_exceeding_threshold:
        # read namespace
        deployment = apps_api.read_namespaced_deployment(name=service_name, namespace='socialnetwork')
        deployment.spec.replicas = services[service_name]['instances'] + 1

        # patch namespace
        apps_api.patch_namespaced_deployment(name=service_name, namespace='socialnetwork', body=deployment)

        services[service_name]['instances'] += 1  # update the number of instances in the service list
        print(f"↑ {service_name} scaled UP to {services[service_name]['instances']} instance(s)")
        time.sleep(AFTER_GRACE_PERIOD)  # wait before allowing to scale up or down again

    running_threads.remove(f"{service_name}")  # remove thread from list so that it can run again


def scale_down(service_name, reduction):
    """Scales down the given service"""
    time.sleep(SCALE_DOWN_GRACE_PERIOD)  # check after grace period before scaling

    response_time = services[service_name]['response_time'][0]
    cpu_util = float(services[service_name]['cpu_utilisation'][0])
    cpu_throttling = float(services[service_name]['cpu_throttling'][0])

    still_under_threshold = (response_time < SCALE_DOWN_THRESHOLD_RESPONSE_TIME 
                                 and cpu_util < SCALE_DOWN_THRESHOLD_UTILISATION 
                                 and cpu_throttling < SCALE_DOWN_THRESHOLD_THROTTLING)

    if still_under_threshold:
        # read namespace
        deployment = apps_api.read_namespaced_deployment(name=service_name, namespace='socialnetwork')
        deployment.spec.replicas = services[service_name]['instances'] - reduction

        # patch namespace
        apps_api.patch_namespaced_deployment(name=service_name, namespace='socialnetwork', body=deployment)

        services[service_name]['instances'] -= reduction  # update the number of instances in the service list
        print(f"↓ {service_name} scaled DOWN to {services[service_name]['instances']} instance(s)")
        time.sleep(AFTER_GRACE_PERIOD)  # wait before allowing to scale up or down again

    running_threads.remove(f"{service_name}")  # remove thread from list so that it can run again


if __name__ == "__main__":
    main()