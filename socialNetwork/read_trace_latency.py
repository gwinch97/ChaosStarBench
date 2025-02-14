import json
from matplotlib import pyplot as plt
import datetime

with open('jaeger_traces.json', 'r') as file:
    data = json.load(file)

data = sorted(data, key=lambda x: x["startTimeMillis"])
timestamps = [datetime.datetime.fromtimestamp(entry["startTimeMillis"]/1000) for entry in data]
durations = []

for entry in data:
    durations.append(entry['duration'])

    # Plot the data
plt.figure(figsize=(10, 5))
plt.plot(timestamps, durations, label='Duration (ms)')
plt.xlabel("Time")
plt.ylabel("Duration (ms)")
plt.title("Span Duration Over Time (NetworkChaos applied at 30s)")
plt.legend()
plt.grid()

# Show plot
plt.savefig('figure.png')