"""This file creates a time-series graph for the number of instances against the number of requests"""

from datetime import datetime
from kubernetes import client, config
from kubernetes.client import ApiException
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sys
import time

try:
    if (len(sys.argv) != 4):
        print("Usage: python3 graph_generator.py {reqs per second} {workload length} {workload type}")
        exit()

    # workload specific variables (please change accordingly)
    REQUESTS_PER_SECOND = int(sys.argv[1]) # change this to the number of requests per second sent to wrk2
    WORKLOAD_LENGTH_SECONDS = int(sys.argv[2]) # change this to the number of seconds the wrk2 workload is running
    WORKLOAD_TYPE = sys.argv[3]
except Exception:
    print("Usage: python3 graph_generator.py {reqs per second} {workload length} {workload type}")
    exit()

# KUBERNETES APIS
try:
    config.load_kube_config()
    core_api = client.CoreV1Api()
    apps_api = client.AppsV1Api()
    autoscale_api = client.AutoscalingV1Api()
except Exception:
    print("Unable to connect to Kubernetes")
    exit()

now = datetime.now()
timesteps = list(range(1, WORKLOAD_LENGTH_SECONDS + 1))
requests_history = []
instance_history = {
    "post-storage-service": [],
    "user-mention-service": [],
    "user-service": [],
    "unique-id-service": [],
    "media-service": [],
    "social-graph-service": [],
    "url-shorten-service": [],
    "compose-post-service": [],
    "user-timeline-service": [],
    "home-timeline-service": [],
    "text-service": []}


def get_replicas(namespace):
    """Attempts to get the amount of replicas for each pod"""
    try:
        for microservice_name in instance_history.keys():
            try:
                # get current number of replicas
                deployment = apps_api.read_namespaced_deployment(name=microservice_name, namespace=namespace)
                instance_history[microservice_name].append(deployment.spec.replicas)
            except ApiException:
                pass

    except Exception as e:
        print(e)


def main():
    requests = 0

    # TODO: make it use jaeger traces instead
    for i in range(0, WORKLOAD_LENGTH_SECONDS): # run for WORKLOAD_LENGTH_SECONDS seconds
        get_replicas('socialnetwork')

        requests += REQUESTS_PER_SECOND
        requests_history.append(requests)

        time.sleep(1)
    
    fig, ax1 = plt.subplots(figsize=(10,5))
    ax1.set_xlabel('Time Steps')
    ax1.set_ylabel('Number of Requests')
    ax1.plot(timesteps, requests_history, linestyle=':', color='black', label='requests')
    plt.xticks(np.arange(0, WORKLOAD_LENGTH_SECONDS + 1, 1))
    
    ax2 = ax1.twinx()
    ax2.set_ylabel('Number of Instances')
    ax2.set_yticks(np.arange(0, 6, 1))
    ax2.set_ylim(0, 5)
    for ms_name, instance_list in instance_history.items():
        ax2.plot(timesteps, instance_list, linestyle='-', label=ms_name)
    
    plt.title(f"Time Series of Requests and Microservice Instances ({WORKLOAD_TYPE})")
    fig.tight_layout()
    plt.grid(True)
    plt.legend()
    plt.savefig(f"experiments/workload-generation/results/{WORKLOAD_TYPE}-{datetime.now()}.png")

if __name__ == "__main__":
    main()