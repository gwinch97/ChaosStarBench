import threading
import time

import requests
from kubernetes import client, config
from kubernetes.client import ApiException

# get deployment IP addresses and ports
ip_address = "127.0.0.1"
jaeger_port = 16686
prom_port = 9090

# scaling specific settings
scale_down_threshold = 40  # cpu usage % when you need to scale down
scale_down_grace_period = 30  # time in seconds between staying at the threshold and scaling down
scale_up_threshold = 85  # cpu usage % when you need to scale up
scale_up_grace_period = 5  # time in seconds between staying at the threshold and scaling up
after_grace_period = 30  # time in seconds after scaling to wait before scaling again
minimum_instances = 1  # min amount of instances of each service
maximum_instances = 5  # max amount of instances of each service

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
    # kubernetes APIs
    config.load_kube_config()

    core_api = client.CoreV1Api()
    apps_api = client.AppsV1Api()
    autoscale_api = client.AutoscalingV1Api()

    print("Running Autoscaling Script")

    # disable HPA and replicas to ensure you can scale with custom metrics
    disable_hpa("socialnetwork", core_api, autoscale_api)
    disable_replicas("socialnetwork", core_api, apps_api)

    # ready to begin gathering data and scaling up
    start_scaling(apps_api)


def remove_hex_code(pod_name):
    return "-".join(pod_name.split("-")[:-2])


def disable_hpa(namespace, core_api, autoscale_api):
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


def disable_replicas(namespace, core_api, apps_api):
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


def start_scaling(apps_api):
    try:
        while True:
            # GET JAEGER TRACE LATENCY
            url = f"http://{ip_address}:{jaeger_port}/api/traces"
            for service_name in services.keys():
                params = {
                    "service": service_name,
                    "lookback": "15m",
                    "limit": 500
                }
                response = requests.get(url, params)
                if response.status_code != 200:
                    print(f"Error while fetching traces for {service_name}: {response.status_code}")
                    continue
                try:
                    traces = response.json()["data"]
                except ValueError:
                    print(f"Invalid JSON response for {service_name}")
                    continue

                total_duration = 0
                span_count = 0

                for trace in traces:
                    for span in trace["spans"]:
                        total_duration += span["duration"]
                        span_count += 1

                services[service_name]['duration'] = total_duration / span_count if (span_count > 0) else 0

            # GET PROMETHEUS CPU USAGE
            # rate(container_cpu_usage_seconds_total{namespace=~"socialnetwork", pod=~".*service.*"}[1m])
            url = f"http://{ip_address}:{prom_port}/api/v1/query?query=container_cpu_usage_seconds_total{{namespace='socialnetwork', pod=~'.*service.*'}}[1m]"
            response = requests.get(url)

            metrics = response.json()["data"]["result"]

            for metric in metrics:
                pod = metric["metric"]["pod"]
                values = metric["values"]

                cpu_usage = 0
                for value in values:
                    cpu_usage += float(value[1])
                services[remove_hex_code(pod)]['cpu'] = cpu_usage

            # GET PROMETHEUS MEMORY USAGE
            # rate(container_memory_usage_bytes{namespace=~"socialnetwork", pod=~".*service.*"}[1m])
            url = f"http://{ip_address}:{prom_port}/api/v1/query?query=container_memory_usage_bytes{{namespace='socialnetwork', pod=~'.*service.*'}}[1m]"
            response = requests.get(url)

            metrics = response.json()["data"]["result"]

            for metric in metrics:
                pod = metric["metric"]["pod"]
                values = metric["values"]

                mem_usage = 0
                for value in values:
                    mem_usage += float(value[1])
                services[remove_hex_code(pod)]['mem'] = mem_usage / (1024 ** 2)  # get usage from bytes to megabytes

            # os.system('clear')
            for service_name in services.keys():
                # print the data into a fixed width table
                # print(f"{service_name:<{30}}"
                #       f"| CPU: {f'{float(services[service_name]['cpu']):.2f}%':<{8}}"
                #       f"| MEM: {f'{float(services[service_name]['mem']):.2f}MB':<{10}}"
                #       f"| LATENCY: {f'{float(services[service_name]["duration"]):.2f}ms':<{10}}")

                # check if you need to scale the service
                # based on whether you are allowed to add or remove instances
                # and whether they are already attempting to scale
                if (services[service_name]['instances'] < maximum_instances
                        and service_name not in threads
                        and float(services[service_name]['cpu']) > scale_up_threshold):
                    thread = threading.Thread(target=scale_up, args=(service_name, apps_api), name=f"{service_name}")
                    threads.append(f"{service_name}")
                    thread.start()
                elif (services[service_name]['instances'] > minimum_instances
                      and service_name not in threads
                      and float(services[service_name]['cpu']) < scale_down_threshold):
                    thread = threading.Thread(target=scale_down, args=(service_name, apps_api), name=f"{service_name}")
                    threads.append(f"{service_name}")
                    thread.start()

            # stop for a few seconds before running again
            time.sleep(10)
    except KeyboardInterrupt:
        exit()  # when user presses Ctrl+C
    except:
        print("Connection Reset Error: Retrying in 30 seconds")
        time.sleep(30)
        pass


def scale_up(service_name, apps_api):
    print(f"{service_name} hit >{scale_up_threshold}% CPU, checking if it is a good idea to scale up.")
    print(f"Entering thread {threading.current_thread().name}")
    time.sleep(scale_up_grace_period)  # check after grace period before scaling

    if float(services[service_name]['cpu']) > scale_up_threshold:
        # scale up
        deployment = apps_api.read_namespaced_deployment(name=service_name, namespace='socialnetwork')
        deployment.spec.replicas = services[service_name]['instances'] + 1

        # scale up
        apps_api.patch_namespaced_deployment(
            name=service_name,
            namespace='socialnetwork',
            body=deployment
        )

        services[service_name]['instances'] += 1 # update the number of instances in the service list
        print(f"{service_name} scaled UP to {services[service_name]['instances']} instance(s)")
        time.sleep(after_grace_period) # wait before allowing to scale up or down again

    print(f"Exiting thread {threading.current_thread().name}.")
    threads.remove(f"{service_name}")  # remove thread from list so that it can run again


def scale_down(service_name, apps_api):
    print(f"{service_name} hit <{scale_down_threshold}% CPU, checking if it is a good idea to scale down.")
    print(f"Entering thread {threading.current_thread().name}")
    time.sleep(scale_down_grace_period)  # check after grace period before scaling

    if float(services[service_name]['cpu']) < scale_down_threshold:
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
        time.sleep(after_grace_period)  # wait before allowing to scale up or down again

    print(f"Exiting thread {threading.current_thread().name}.")
    threads.remove(f"{service_name}")  # remove thread from list so that it can run again


if __name__ == "__main__":
    main()
