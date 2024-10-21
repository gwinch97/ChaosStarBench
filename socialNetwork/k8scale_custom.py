from kubernetes import client, config, watch
import requests
import time

def main():
    config.load_kube_config()

    core_api = client.CoreV1Api()
    apps_api = client.AppsV1Api()
    autoscale_api = client.AutoscalingV1Api()

    # disable HPA and replicas to ensure you can scale with custom metrics
    disable_hpa("socialnetwork", core_api, autoscale_api)
    disable_replicas("socialnetwork", core_api, apps_api)

def disable_hpa(namespace, core_api, autoscale_api):
    try:
        pods = core_api.list_namespaced_pod(namespace=namespace).items

        for pod in pods:
            # extract name of pod without the hex codes
            resource_name = '-'.join(pod.metadata.name.split('-')[:-2])

            try:
                # disable HPA and add pod to disabled set
                autoscale_api.delete_namespaced_horizontal_pod_autoscaler(
                    name=resource_name,
                    namespace=namespace,
                )
                print(f"Ensure HPA Disabled: {resource_name}")
            except Exception as e:
                print(f"Ensure HPA Disabled: {resource_name}")
                pass

    except Exception as e:
        print(f"Unexpected Exception: {e}")

def disable_replicas(namespace, core_api, apps_api):
    try:
        pods = core_api.list_namespaced_pod(namespace=namespace).items
        for pod in pods:
            # extract name of pod without the hex codes
            resource_name = '-'.join(pod.metadata.name.split('-')[:-2])

            try:
                # remove all replicas
                deployment = apps_api.read_namespaced_deployment(name=resource_name, namespace=namespace)
                deployment.spec.replicas = 1
                # apply replica reduction
                apps_api.patch_namespaced_deployment(name=resource_name, namespace=namespace, body=deployment)
                print(f"Ensure Replica Removal: {resource_name}")
            except Exception as e:
                print(f"Ensure Replica Removal: {resource_name}")
                pass

    except Exception as e:
        print(e)

if __name__ == "__main__":
    main()










'''
try:
    config.load_kube_config()
    core_api = client.CoreV1Api()
    apps_api = client.AppsV1Api()
    namespaces = core_api.list_namespace()
    for namespace in namespaces.items:
        namespace_name = namespace.metadata.name
        pods = core_api.list_namespaced_pod(namespace=namespace_name, watch=False).items
        if len(pods) > 0:
            print(f"---{namespace_name}---")

            for pod in pods:
                pod_name = pod.metadata.name
                print(pod_name, f"({pod.status.pod_ip})")

            print("")
except Exception as e:
    print(e)
    print("Ensure that Kubernetes is running before opening this script.")
    quit()

LIST SERVICES CAUGHT BY JAEGER
http_response = requests.get("http://localhost:16686/api/services")
services = http_response.json()
for service in services["data"]:
    print("SERVICE:", service)

try:
    traces = requests.get("http://localhost:16686/api/traces", params={"service":"user-service"})
    strings = traces.json()
    for s in strings["data"]:
        print("TRACE:", s["spans"][1]["operationName"], f"({s["spans"][4]["duration"]}ms)")
except Exception as e:
    print(e)
    print("Ensure the port for Jaeger is forwarded before opening this script.")
    quit()
'''