"""Validate every chaos/<fault>/<service>.yaml against the Chaos Mesh CRD schemas in ../chaos-mesh/crds,
and check each targets the hotelReservation pod label the Helm chart actually uses."""
import glob, os, subprocess, sys, yaml, jsonschema

here = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(here)
crds = {}
for f in glob.glob(os.path.join(root, "..", "chaos-mesh", "crds", "*.yaml")):
    for doc in yaml.safe_load_all(open(f)):
        if doc and doc.get("kind") == "CustomResourceDefinition":
            kind = doc["spec"]["names"]["kind"]
            for v in doc["spec"]["versions"]:
                if v["name"] == "v1alpha1":
                    crds[kind] = v["schema"]["openAPIV3Schema"]
render = subprocess.run(["helm", "template", "hotelres", os.path.join(root, "..", "hotelReservation/helm-chart/hotelreservation"),
                         "-n", "hotelreservation", "-f", os.path.join(root, "values-fcadl.yaml")],
                        capture_output=True, text=True, check=True).stdout
pod_apps = {d["spec"]["template"]["metadata"]["labels"]["app"]
            for d in yaml.safe_load_all(render) if d and d.get("kind") == "Deployment"}
bad = 0
files = sorted(glob.glob(os.path.join(root, "chaos", "*", "*.yaml")))
for f in files:
    m = yaml.safe_load(open(f))
    try:
        jsonschema.validate(m, crds[m["kind"]])
    except Exception as e:
        bad += 1; print("SCHEMA FAIL", f, str(e)[:200])
    app = m["spec"]["selector"]["labelSelectors"]["app"]
    if app not in pod_apps:
        bad += 1; print("NO SUCH POD LABEL", f, app)
print(f"{len(files)} manifests checked against {sorted(crds)[:0] or len(crds)} CRD schemas; failures: {bad}")
sys.exit(1 if bad else 0)
