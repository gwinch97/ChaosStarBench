import os
import time

import requests
from kubernetes import client, config
from kubernetes.client import ApiException

ip_address = "127.0.0.1"
jaeger_port = 16686
prom_port = 9090

# map of services that can be scaled
services = {"post-storage-service": {"duration": 0, "cpu": 0, "mem": 0},
            "user-mention-service": {"duration": 0, "cpu": 0, "mem": 0},
            "user-service": {"duration": 0, "cpu": 0, "mem": 0},
            "unique-id-service": {"duration": 0, "cpu": 0, "mem": 0},
            "media-service": {"duration": 0, "cpu": 0, "mem": 0},
            "social-graph-service": {"duration": 0, "cpu": 0, "mem": 0},
            "url-shorten-service": {"duration": 0, "cpu": 0, "mem": 0},
            "compose-post-service": {"duration": 0, "cpu": 0, "mem": 0},
            "user-timeline-service": {"duration": 0, "cpu": 0, "mem": 0},
            "home-timeline-service": {"duration": 0, "cpu": 0, "mem": 0},
            "text-service": {"duration": 0, "cpu": 0, "mem": 0}}


def main():
    config.load_kube_config()

    core_api = client.CoreV1Api()
    apps_api = client.AppsV1Api()
    autoscale_api = client.AutoscalingV1Api()

    # disable HPA and replicas to ensure you can scale with custom metrics
    disable_hpa("socialnetwork", core_api, autoscale_api)
    disable_replicas("socialnetwork", core_api, apps_api)

    # ready to begin gathering data and scaling up
    start_scaling()


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
            except ApiException as e:
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
                # print(f"Disable Replicas: {resource_name}") # for debugging
            except ApiException as e:
                pass

    except Exception as e:
        print(e)


def start_scaling():
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

            traces = response.json()["data"]

            total_duration = 0
            span_count = 0

            for trace in traces:
                for span in trace["spans"]:
                    total_duration += span["duration"]
                    span_count += 1

            services[service_name]['duration'] = total_duration / span_count if (span_count > 0) else 0

        # GET PROMETHEUS CPU USAGE
        # rate(container_cpu_usage_seconds_total{namespace=~"socialnetwork", pod=~".*service.*"}[15s])
        url = f"http://{ip_address}:{prom_port}/api/v1/query?query=container_cpu_usage_seconds_total{{namespace='socialnetwork', pod=~'.*service.*'}}[15s]"
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
        # rate(container_memory_usage_bytes{namespace=~"socialnetwork", pod=~".*service.*"}[15s])
        url = f"http://{ip_address}:{prom_port}/api/v1/query?query=container_memory_usage_bytes{{namespace='socialnetwork', pod=~'.*service.*'}}[15s]"
        response = requests.get(url)

        metrics = response.json()["data"]["result"]

        for metric in metrics:
            pod = metric["metric"]["pod"]
            values = metric["values"]

            mem_usage = 0
            for value in values:
                mem_usage += float(value[1])
            services[remove_hex_code(pod)]['mem'] = mem_usage / 1024  # get usage from bytes to megabytes

        # print values to the console
        os.system('clear')
        for service_name in services.keys():
            print(f"{service_name:<{30}}"  # force the data into a fixed width table
                  f"| CPU: {f'{float(services[service_name]['cpu']):.2f}%':<{10}}"
                  f"| MEM: {f'{float(services[service_name]['mem']):.2f}MB':<{10}}"
                  f"| LATENCY: {f'{float(services[service_name]["duration"]):.2f}ms':<{10}}")

        # stop for 15 few seconds before running again
        time.sleep(15)


if __name__ == "__main__":
    main()
