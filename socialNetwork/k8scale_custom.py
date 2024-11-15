import os
from datetime import datetime

import time
import requests
from kubernetes import client, config
from kubernetes.client import ApiException

ip_address = "127.0.0.1"
jaeger_port = 16686
prom_port = 9090

services = {"post-storage-service": 0, "user-mention-service": 0, "post-storage-memcached": 0, "nginx-thrift": 0,
            "social-graph-redis": 0, "user-service": 0, "media-memcached": 0, "unique-id-service": 0,
            "user-mongodb": 0, "media-frontend": 0, "user-timeline-redis": 0, "user-memcached": 0,
            "url-shorten-mongodb": 0, "home-timeline-redis": 0, "media-service": 0, "social-graph-service": 0,
            "media-mongodb": 0, "url-shorten-memcached": 0, "social-graph-mongodb": 0, "user-timeline-mongodb": 0,
            "post-storage-mongodb": 0, "url-shorten-service": 0, "compose-post-service": 0,
            "user-timeline-service": 0, "home-timeline-service": 0}


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


def disable_hpa(namespace, core_api, autoscale_api):
    try:
        pods = core_api.list_namespaced_pod(namespace=namespace).items

        for pod in pods:
            # extract name of pod without the hex codes
            resource_name = "-".join(pod.metadata.name.split("-")[:-2])

            try:
                # disable HPA
                autoscale_api.delete_namespaced_horizontal_pod_autoscaler(
                    name=resource_name,
                    namespace=namespace,
                )
                # print(f"Disable HPA: {resource_name}") # for debugging
            except ApiException as e:
                pass

    except Exception as e:
        print(f"Unexpected Exception: {e}")


def disable_replicas(namespace, core_api, apps_api):
    try:
        pods = core_api.list_namespaced_pod(namespace=namespace).items
        for pod in pods:
            # extract name of pod without the hex codes
            resource_name = "-".join(pod.metadata.name.split("-")[:-2])

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
        os.system('clear')

        # get jaeger trace latency
        url = f"http://{ip_address}:{jaeger_port}/api/traces"
        for service_name in services.keys():
            params = {
                "service": service_name,
                "lookback": "1h",
                "limit": 100
            }
            response = requests.get(url, params)

            traces = response.json()["data"]

            total_duration = 0
            span_count = 0

            for trace in traces:
                for span in trace["spans"]:
                    total_duration += span["duration"]
                    span_count += 1

            services[service_name] = total_duration / span_count if (span_count > 0) else 0

        for service_name in services.keys():
            print(service_name, services[service_name])

        # get prometheus cpu usage
        # rate(container_cpu_usage_seconds_total{namespace=~"socialnetwork",pod!~"cadvisor.+|prometheus.+|ngin.+"}[15s])
        url = f"http://{ip_address}:{prom_port}/api/v1/query?query=container_cpu_usage_seconds_total{{namespace='socialnetwork', pod!~'.*cadvisor.*|.*prometheus.*|.*jaeger.*'}}[15s]"  # every 15s sample freq
        response = requests.get(url)

        metrics = response.json()["data"]["result"]

        for metric in metrics:
            pod = metric["metric"]["pod"]
            values = metric["values"]
            for value in values:
                # timestamp = datetime.fromtimestamp(value[0])
                utilisation = value[1]
                # print(f"{pod} {utilisation}%")

        # get prometheus memory usage

        # stop for a few seconds before running again
        time.sleep(5)


if __name__ == "__main__":
    main()