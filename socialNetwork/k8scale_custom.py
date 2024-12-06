import threading
import time
import json
import requests
from elasticsearch import Elasticsearch, helpers
from kubernetes import client, config
from kubernetes.client import ApiException
from tqdm import tqdm

# get deployment IP addresses and ports
IP_ADDRESS = "127.0.0.1"
ELASTICSEARCH_PORT = 9200
JAEGER_PORT = 16686
PROM_PORT = 9090

# scaling specific settings
SCALE_DOWN_THRESHOLD = 40  # cpu usage % when you need to scale down
SCALE_DOWN_GRACE_PERIOD = 30  # time in seconds between staying at the threshold and scaling down
SCALE_UP_THRESHOLD = 85  # cpu usage % when you need to scale up
SCALE_UP_GRACE_PERIOD = 5  # time in seconds between staying at the threshold and scaling up
AFTER_GRACE_PERIOD = 30  # time in seconds after scaling to wait before scaling again
MINIMUM_INSTANCES = 1  # min amount of instances of each service
MAXIMUM_INSTANCES = 5  # max amount of instances of each service

# kubernetes APIs
config.load_kube_config()

core_api = client.CoreV1Api()
apps_api = client.AppsV1Api()
autoscale_api = client.AutoscalingV1Api()

# prevent methods being called on multiple threads
threads = []  # list of currently running threads

# map of services that can be scaled
services = {"post-storage-service": {"duration": 0, "cpu": 0, "mem": 0, "instances": 1},
            "user-mention-service": {"duration": 0, "cpu": 0, "mem": 0, "instances": 1},
            "user-service": {"duration": 0, "cpu": 0, "mem": 0, "instances": 1},
            "unique-id-service": {"duration": 0, "cpu": 0, "mem": 0, "instances": 1},
            "media-service": {"duration": 0, "cpu": 0, "mem": 0, "instances": 1},
            "social-graph-service": {"duration": 0, "cpu": 0, "mem": 0, "instances": 1},
            "url-shorten-service": {"duration": 0, "cpu": 0, "mem": 0, "instances": 1},
            "compose-post-service": {"duration": 0, "cpu": 0, "mem": 0, "instances": 1},
            "user-timeline-service": {"duration": 0, "cpu": 0, "mem": 0, "instances": 1},
            "home-timeline-service": {"duration": 0, "cpu": 0, "mem": 0, "instances": 1},
            "text-service": {"duration": 0, "cpu": 0, "mem": 0, "instances": 1}}


def main():
    print("Running Autoscaling Script")

    # disable HPA and replicas to ensure you can scale with custom metrics
    disable_hpa("socialnetwork")
    disable_replicas("socialnetwork")

    # ready to begin gathering data and scaling up
    start_scaling()


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


def start_scaling():
    try:
        es = Elasticsearch([{'host': IP_ADDRESS, 'port': ELASTICSEARCH_PORT, 'scheme': 'http'}])
        # rate(container_cpu_usage_seconds_total{namespace=~"socialnetwork", pod=~".*service.*"}[1m])
        prom_cpu_url = f"http://{IP_ADDRESS}:{PROM_PORT}/api/v1/query?query=container_cpu_usage_seconds_total{{namespace='socialnetwork', pod=~'.*service.*'}}[1m]"
        # rate(container_memory_usage_bytes{namespace=~"socialnetwork", pod=~".*service.*"}[1m])
        prom_mem_url = f"http://{IP_ADDRESS}:{PROM_PORT}/api/v1/query?query=container_memory_usage_bytes{{namespace='socialnetwork', pod=~'.*service.*'}}[1m]"
        INDEX_PATTERN = "jaeger-span-*"
        OUTPUT_FILE = "jaeger_traces.json"

        while True:
            # GET JAEGER TRACE LATENCY
            # Initialize the scroll
            scroll = '2m'
            batch_size = 1000

            # Initialize the query (match all - maybe change to only match the root of the trace?)
            query = {
                "query": {
                    "match_all": {}
                }
            }

            scroll_gen = helpers.scan(
                client=es,
                index=INDEX_PATTERN,
                query=query,
                scroll=scroll,
                size=batch_size,
                preserve_order=False
            )

            # Open the output file
            with open(OUTPUT_FILE, 'w') as f:
                f.write('[')
                first = True
                total = es.count(index=INDEX_PATTERN)['count']
                with tqdm(total=total, desc="Exporting Traces") as pbar:
                    for doc in scroll_gen:
                        trace = doc['_source']
                        # Could process or filter trace before saving
                        if not first:
                            f.write(',\n')
                        else:
                            first = False
                        json.dump(trace, f)
                        pbar.update(1)
                f.write(']')

            print(f"Export completed. Traces saved to {OUTPUT_FILE}")

            # GET PROMETHEUS CPU USAGE
            response = requests.get(prom_cpu_url)

            metrics = response.json()["data"]["result"]

            for metric in metrics:
                pod = metric["metric"]["pod"]
                values = metric["values"]

                cpu_usage = 0
                for value in values:
                    cpu_usage += float(value[1])
                services[remove_hex_code(pod)]['cpu'] = cpu_usage

            # GET PROMETHEUS MEMORY USAGE
            response = requests.get(prom_mem_url)

            metrics = response.json()["data"]["result"]

            for metric in metrics:
                pod = metric["metric"]["pod"]
                values = metric["values"]

                mem_usage = 0
                for value in values:
                    mem_usage += float(value[1])
                services[remove_hex_code(pod)]['mem'] = mem_usage / (1024 ** 2)  # get usage from bytes to megabytes

            print("--------------------------------------------------")
            for service_name in services.keys():
                # print the data into a fixed width table
                print(f"{service_name:<{30}}"
                    f"| LATENCY: {f'{float(services[service_name]["duration"]):.2f}ms':<{10}}"
                    f"| CPU: {f'{float(services[service_name]['cpu']):.2f}%':<{8}}"
                    f"| MEM: {f'{float(services[service_name]['mem']):.2f}MB':<{10}}")

                # check if you need to scale the service
                # based on whether you are allowed to add or remove instances
                # and whether they are already attempting to scale
                if (services[service_name]['instances'] < MAXIMUM_INSTANCES
                        and service_name not in threads
                        and float(services[service_name]['cpu']) > (SCALE_UP_THRESHOLD * services[service_name]['instances'])):
                    thread = threading.Thread(target=scale_up, args=(service_name,), name=f"{service_name}")
                    threads.append(f"{service_name}")
                    thread.start()
                elif (services[service_name]['instances'] > MINIMUM_INSTANCES
                    and service_name not in threads
                    and float(services[service_name]['cpu']) < SCALE_DOWN_THRESHOLD):
                    thread = threading.Thread(target=scale_down, args=(service_name,), name=f"{service_name}")
                    threads.append(f"{service_name}")
                    thread.start()

            # stop for a few seconds before running again
            time.sleep(10)
    except KeyboardInterrupt:
        exit()  # when user presses Ctrl+C
    # except:
    #     print("Connection Reset Error: Retrying in 30 seconds")
    #     time.sleep(30)
    #     pass


def scale_up(service_name):
    print(f"{service_name} hit >{SCALE_UP_THRESHOLD}% CPU")
    print(f"Checking if it is a good idea to scale up on thread '{threading.current_thread().name}'.")
    time.sleep(SCALE_UP_GRACE_PERIOD)  # check after grace period before scaling

    if float(services[service_name]['cpu']) > SCALE_UP_THRESHOLD:
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
        print(f"{service_name} scaled UP to {services[service_name]['instances']} instance(s)")
        time.sleep(AFTER_GRACE_PERIOD)  # wait before allowing to scale up or down again

    print(f"Exiting thread {threading.current_thread().name}.")
    threads.remove(f"{service_name}")  # remove thread from list so that it can run again


def scale_down(service_name):
    print(f"{service_name} hit <{SCALE_DOWN_THRESHOLD}% CPU")
    print(f"Checking if it is a good idea to scale down on thread '{threading.current_thread().name}'.")
    time.sleep(SCALE_DOWN_GRACE_PERIOD)  # check after grace period before scaling

    if float(services[service_name]['cpu']) < SCALE_DOWN_THRESHOLD:
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
        print(f"{service_name} scaled DOWN to {services[service_name]['instances']} instance(s)")
        time.sleep(AFTER_GRACE_PERIOD)  # wait before allowing to scale up or down again

    print(f"Exiting thread {threading.current_thread().name}.")
    threads.remove(f"{service_name}")  # remove thread from list so that it can run again


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
# step 6:   calculate exploration probability to decide whether or not to try a previously 
#           stable resource allocation configuration (then go back to step 1)
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
