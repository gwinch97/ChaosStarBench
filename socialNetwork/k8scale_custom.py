import json
import os
import threading
import time

import requests
from elasticsearch import Elasticsearch, helpers
from kubernetes import client, config
from kubernetes.client import ApiException

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
SCALE_DOWN_THRESHOLD_UTILISATION = 45.0  # cpu utilisation % when you need to scale down
SCALE_DOWN_THRESHOLD_THROTTLING = 2.5  # cpu throttle % when you need to scale down
SCALE_DOWN_GRACE_PERIOD = 15  # time in seconds between first meeting the threshold and then scaling down
SCALE_UP_THRESHOLD_UTILISATION = 85.0  # cpu utilisation % when you need to scale up
SCALE_UP_THRESHOLD_THROTTLING = 10.0  # cpu throttling % when you need to scale up
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

# DICT OF SERVICE INFORMATION
services = {"post-storage-service": {"response_time": 0, "cpu_utilisation": 0.0, "cpu_throttling": 0.0, "instances": 1},
            "user-mention-service": {"response_time": 0, "cpu_utilisation": 0.0, "cpu_throttling": 0.0, "instances": 1},
            "user-service": {"response_time": 0, "cpu_utilisation": 0.0, "cpu_throttling": 0.0, "instances": 1},
            "unique-id-service": {"response_time": 0, "cpu_utilisation": 0.0, "cpu_throttling": 0.0, "instances": 1},
            "media-service": {"response_time": 0, "cpu_utilisation": 0.0, "cpu_throttling": 0.0, "instances": 1},
            "social-graph-service": {"response_time": 0, "cpu_utilisation": 0.0, "cpu_throttling": 0.0, "instances": 1},
            "url-shorten-service": {"response_time": 0, "cpu_utilisation": 0.0, "cpu_throttling": 0.0, "instances": 1},
            "compose-post-service": {"response_time": 0, "cpu_utilisation": 0.0, "cpu_throttling": 0.0, "instances": 1},
            "user-timeline-service": {"response_time": 0, "cpu_utilisation": 0.0, "cpu_throttling": 0.0,
                                      "instances": 1},
            "home-timeline-service": {"response_time": 0, "cpu_utilisation": 0.0, "cpu_throttling": 0.0,
                                      "instances": 1},
            "text-service": {"response_time": 0, "cpu_utilisation": 0.0, "cpu_throttling": 0.0, "instances": 1}}


def main():
    print("Running Autoscaling Script")

    # disable HPA and replicas to ensure you can scale with custom metrics
    disable_hpa("socialnetwork")
    disable_replicas("socialnetwork")

    # ready to begin gathering data and scaling up
    autoscale()


def remove_hex_code(pod_name):
    return "-".join(pod_name.split("-")[:-2])


def disable_hpa(namespace):
    try:
        pods = core_api.list_namespaced_pod(namespace=namespace).items

        for pod in pods:
            # extract name of pod without the hex code at the end
            resource_name = remove_hex_code(pod.metadata.name)

            try:
                # disable HPA for every service to ensure there are no conflicts with this script
                autoscale_api.delete_namespaced_horizontal_pod_autoscaler(
                    name=resource_name,
                    namespace=namespace,
                )
            except ApiException:
                pass

    except Exception as e:
        print(f"Unexpected Exception: {e}")


def disable_replicas(namespace):
    try:
        pods = core_api.list_namespaced_pod(namespace=namespace).items
        for pod in pods:
            # extract name of pod without the hex codes
            resource_name = remove_hex_code(pod.metadata.name)

            try:
                # remove all replicas
                deployment = apps_api.read_namespaced_deployment(
                    name=resource_name,
                    namespace=namespace
                )
                deployment.spec.replicas = 1
                # apply replica reduction
                apps_api.patch_namespaced_deployment(
                    name=resource_name,
                    namespace=namespace,
                    body=deployment
                )
            except ApiException:
                pass

    except Exception as e:
        print(e)


def autoscale():
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
            query = {
                "_source": ["process.serviceName", "duration"],
                "query": {
                    "range": {
                        "startTimeMillis": {
                            "gte": epoch_time_10s_ago
                        }
                    }
                }
            }

            total = es.count(index=index_pattern, body={"query": query['query']})['count']

            if total != 0:
                scroll_gen = helpers.scan(
                    client=es,
                    index=index_pattern,
                    query=query,
                    scroll=scroll,
                    size=batch_size,
                    preserve_order=False
                )

                # Open the output file
                with open(OUTPUT_FILE, 'w') as f:
                    f.write('[')
                    first = True
                    for doc in scroll_gen:
                        trace = doc['_source']

                        if not first:
                            f.write(',\n')
                        else:
                            first = False

                        json.dump(trace, f)
                    f.write(']')

                # TODO: Make it such that the latency average is sent to the services dictionary

            # GET PROMETHEUS CPU USAGE
            response = requests.get(PROM_CPU_UTILISATION)
            metrics = response.json()["data"]["result"]

            for metric in metrics:
                pod = remove_hex_code(metric["metric"]["pod"])  # pod name
                values = metric["values"]  # pod usage as [timestamp, value]

                cpu_usage = float(values[-1][1])  # get most recent value

                if services[pod]['cpu_utilisation'] == 0.0:  # should only be 0 on the first run
                    services[pod]['cpu_utilisation'] = cpu_usage
                else:
                    services[pod]['cpu_utilisation'] = (services[pod]['cpu_utilisation'] + cpu_usage) / 2  # avg

            # GET PROMETHEUS CPU THROTTLING
            response = requests.get(PROM_CPU_THROTTLING)
            metrics = response.json()["data"]["result"]

            for metric in metrics:
                pod = remove_hex_code(metric["metric"]["pod"])  # pod name
                values = metric["values"]  # pod usage as [timestamp, value]

                cpu_throttling = float(values[-1][1])  # get most recent value

                if services[pod]['cpu_throttling'] == 0.0:  # should only be 0 on the first run
                    services[pod]['cpu_throttling'] = cpu_throttling
                else:
                    services[pod]['cpu_throttling'] = (services[pod]['cpu_throttling'] + cpu_throttling) / 2  # avg

            print("--------------------------------------------------")
            for service_name in services.keys():
                instances = services[service_name]["instances"]
                cpu_util = float(services[service_name]['cpu_utilisation'])
                cpu_throttling = float(services[service_name]['cpu_throttling'])
                response_time = float(services[service_name]["response_time"])

                # print the data into a table
                print(f"{service_name:<{22}}"
                      f"| INSTANCES: {f'{instances}x':<{3}}"
                      f"| UTILISATION: {f'{cpu_util:.2f}%':<{8}}"
                      f"| THROTTLING: {f'{cpu_throttling:.2f}%':<{8}}"
                      f"| RESPONSE TIME: {f'{response_time:.2f}ms':<{10}}")

                # check if you need to scale the service
                # based on whether you are allowed to add or remove instances
                # and whether they are already attempting to scale
                if services[service_name]['instances'] < MAXIMUM_INSTANCES and service_name not in running_threads:
                    max_cpu_util = SCALE_UP_THRESHOLD_UTILISATION * services[service_name]['instances']

                    should_scale_up = (
                            cpu_util > max_cpu_util or cpu_throttling > SCALE_UP_THRESHOLD_THROTTLING
                    )

                    if should_scale_up:
                        thread = threading.Thread(target=scale_up, args=(service_name,), name=f"{service_name}")
                        running_threads.append(f"{service_name}")
                        thread.start()
                elif services[service_name]['instances'] > MINIMUM_INSTANCES and service_name not in running_threads:
                    should_scale_down = (
                            cpu_util < SCALE_DOWN_THRESHOLD_UTILISATION and cpu_throttling < SCALE_DOWN_THRESHOLD_THROTTLING
                    )

                    if should_scale_down:
                        thread = threading.Thread(target=scale_down, args=(service_name,), name=f"{service_name}")
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
    time.sleep(SCALE_UP_GRACE_PERIOD)  # check after grace period before scaling

    cpu_util = float(services[service_name]['cpu_utilisation'])
    cpu_throttling = float(services[service_name]['cpu_throttling'])

    if cpu_util > SCALE_UP_THRESHOLD_UTILISATION or cpu_throttling > SCALE_UP_THRESHOLD_THROTTLING:
        # scale up
        deployment = apps_api.read_namespaced_deployment(name=service_name, namespace='socialnetwork')
        deployment.spec.replicas = services[service_name]['instances'] + 1

        # scale up
        apps_api.patch_namespaced_deployment(
            name=service_name,
            namespace='socialnetwork',
            body=deployment
        )

        services[service_name]['instances'] += 1  # update the number of instances in the service list
        print(f"↑ {service_name} scaled UP to {services[service_name]['instances']} instance(s)")
        time.sleep(AFTER_GRACE_PERIOD)  # wait before allowing to scale up or down again

    running_threads.remove(f"{service_name}")  # remove thread from list so that it can run again


def scale_down(service_name):
    time.sleep(SCALE_DOWN_GRACE_PERIOD)  # check after grace period before scaling

    cpu_util = float(services[service_name]['cpu_utilisation'])
    cpu_throttling = float(services[service_name]['cpu_throttling'])

    if cpu_util < SCALE_DOWN_THRESHOLD_UTILISATION and cpu_throttling < SCALE_DOWN_THRESHOLD_THROTTLING:
        # scale down
        deployment = apps_api.read_namespaced_deployment(name=service_name, namespace='socialnetwork')
        deployment.spec.replicas = services[service_name]['instances'] - 1

        # scale up
        apps_api.patch_namespaced_deployment(
            name=service_name,
            namespace='socialnetwork',
            body=deployment
        )

        services[service_name]['instances'] -= 1  # update the number of instances in the service list
        print(f"↓ {service_name} scaled DOWN to {services[service_name]['instances']} instance(s)")
        time.sleep(AFTER_GRACE_PERIOD)  # wait before allowing to scale up or down again

    running_threads.remove(f"{service_name}")  # remove thread from list so that it can run again


if __name__ == "__main__":
    main()

# TODO: Implement efficient scaling algorithm 
#       from 'Practical Efficient Microservice Autoscaling' (Md Rajib Hossen, Mohammad A. Islam)
#
# step 1:   for each time step:
#
# step 2:   grab response time, CPU utilisation and CPU throttling statistics
#
# step 3:   log the performance statistics for future reference
#
# step 4:   check if the response times are too slow and exceed defined limits, 
#           allocate more resources to ensure that the performance is back to acceptable range
#           (then go back to step 1)
#
# step 5:   recalculate safe limits for CPU usage and throttling (using equation 6 and 7 
#           from the paper)
#
# step 6:   calculate exploration probability (equation 8) to decide whether or not to try 
#           a previously stable resource allocation configuration (then go back to step 1)
#
# step 7:   determine a new target resource allocation (reduction) based on a reduction limit
#           (i.e. do not scale down more than 20%) (using equation 3 and 4 from the paper)
#
# step 8:   identify services that are currently throttling or close to utilisation limits,
#           and ensure these services are excluded from resource reductions
#
# step 9:   assign higher probability of reduction to the services that have a lower utilisation,
#           ensuring a more safe approach to scaling down (using equation 5 from the paper)
#
# step 10:  apply step 7 reduction target, ignoring bottleneck services and then uniformly
#           reduce the resources across all non-bottleneck services for next time step
