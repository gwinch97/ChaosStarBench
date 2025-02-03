"""This file creates a time-series graph for the number of instances against the number of requests"""

from kubernetes import client, config
from kubernetes.client import ApiException
import matplotlib
import time

# KUBERNETES APIS
config.load_kube_config()
core_api = client.CoreV1Api()
apps_api = client.AppsV1Api()
autoscale_api = client.AutoscalingV1Api()

requests = 0
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

while True:
    get_replicas('socialnetwork')

    requests += 100
    for k, v in services.items():
        print(requests, k, v['instances'])

    time.sleep(1)