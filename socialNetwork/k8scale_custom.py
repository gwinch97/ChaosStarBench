from kubernetes import client, config

from kubernetes.client import ApiException


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
                # disable HPA
                autoscale_api.delete_namespaced_horizontal_pod_autoscaler(
                    name=resource_name,
                    namespace=namespace,
                )
                print(f"Disable HPA: {resource_name}")
            except ApiException as e:
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
                print(f"Disable Replicas: {resource_name}")
            except ApiException as e:
                pass

    except Exception as e:
        print(e)


if __name__ == "__main__":
    main()

''' keep for later - jaeger http endpoints
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
