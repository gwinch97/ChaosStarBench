import json
import numpy as np
import matplotlib.pyplot as plt
import sys


def get_name(name):
        return "-".join(name.split("-")[:-2])


def main():
    if len(sys.argv) == 2:
        experiment_folder = sys.argv[1]
    else:
        print('Usage: python3 analyse-results.py path_to_results_folder')
        sys.exit(0)

    # load all data
    try:
        with open(f'./{experiment_folder}/prometheus_cpu_utilisation.json', 'r') as cpu_utilisation_file:
            cpu_utilisation_data = json.load(cpu_utilisation_file)
        with open(f'./{experiment_folder}/prometheus_cpu_throttling.json', 'r') as cpu_throttling_file:
            cpu_throttling_data = json.load(cpu_throttling_file)
        with open(f'./{experiment_folder}/prometheus_instance_count.json', 'r') as instance_count_file:
            instance_count_data = json.load(instance_count_file)
        with open(f'./{experiment_folder}/prometheus_io_writes.json', 'r') as io_writes_file:
            io_writes_data = json.load(io_writes_file)
        with open(f'./{experiment_folder}/prometheus_mem_utilisation.json', 'r') as mem_utilisation_file:
            mem_utilisation_data = json.load(mem_utilisation_file)
        with open(f'./{experiment_folder}/prometheus_network_transmit.json', 'r') as network_transmit_file:
            network_transmit_data = json.load(network_transmit_file)
    except FileNotFoundError:
        print(f'Files could not be found at {experiment_folder}')
        sys.exit(0)

    services = {
        "post-storage-service": {},
        "user-mention-service": {},
        "user-service": {},
        "unique-id-service": {},
        "media-service": {},
        "social-graph-service": {},
        "url-shorten-service": {},
        "compose-post-service": {},
        "user-timeline-service": {},
        "home-timeline-service": {},
        "text-service": {}
    }

    cpu_utilisation = services.copy()
    cpu_throttling = services.copy()
    instance_count = services.copy()
    io_writes = services.copy()
    mem_utilisation = services.copy()
    network_transmit = services.copy()

    new_dict = {}
    for result in cpu_utilisation_data['data']['result']:
        ms_name = get_name(result['metric']['pod'])
        if ms_name in new_dict.keys():
            new_dict[ms_name].append(result)
        else:
            new_dict[ms_name] = [result]

    for instance_info in new_dict.values():
        for instance in instance_info:
            start_time = instance['values'][0][0]
            for timestep in instance['values']:
                time = int(timestep[0] - start_time)
                value = float(timestep[1])
                ms_name = get_name(instance['metric']['pod'])
                
                if time not in cpu_utilisation[ms_name]:
                    cpu_utilisation[ms_name][time] = value
                else:
                    cpu_utilisation[ms_name][time] = (cpu_utilisation[ms_name][time] + value) / 2

    for servicename, time_data in cpu_utilisation.items():
        if servicename=='compose-post-service':
            times = list(time_data.keys())
            values = list(time_data.values())
            
            plt.plot(times, values, label=servicename)
            plt.axvline(1800, color='r', linestyle='--')
    plt.xlabel('Time (s)')
    plt.ylabel('CPU Utilisation (%)')
    plt.ylim(0, 0.05)
    plt.title('compose-post-service (networkchaos applied at 1800s)')
    plt.savefig('example.png')


if __name__ == "__main__":
    main()
