# Running Experiments

To run an experiment, you must decide whether you would like to run a Chaos Mesh (pod-level) or chaosd (node-level) fault.

For Chaos Mesh experiments, run:
```bash
bash run_chaos_mesh_experiment.sh <experiment> <severity=low/medium/high> <threads> <connections> <duration> <requests_per_second>
```

For chaosd experiments, run:
```bash
bash run_chaosd_experiment.sh <experiment> <severity=low/medium/high> <threads> <connections> <duration> <requests_per_second>
```

The experiment will then run, and inject chaos halfway through. The results of the experiment will be stored in the 'experiments/results' folder.