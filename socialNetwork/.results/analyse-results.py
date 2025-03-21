import json
import matplotlib.pyplot as plt
import sys


def get_name(name):
        return "-".join(name.split("-")[:-2])


def main():
    if len(sys.argv) == 2:
        experiment_folder = sys.argv[1]
    else:
        print('Usage: python3 analyse-results.py results_folder_name')
        sys.exit(0)

    # load all data
    try:
        with open(f'./{experiment_folder}/prometheus_cpu_utilisation.json', 'r') as cpu_utilisation_file:
            cpu_utilisation_data = json.load(cpu_utilisation_file)['data']['result']
        with open(f'./{experiment_folder}/prometheus_cpu_throttling.json', 'r') as cpu_throttling_file:
            cpu_throttling_data = json.load(cpu_throttling_file)['data']['result']
        with open(f'./{experiment_folder}/prometheus_instance_count.json', 'r') as instance_count_file:
            instance_count_data = json.load(instance_count_file)['data']['result']
        with open(f'./{experiment_folder}/prometheus_io_writes.json', 'r') as io_writes_file:
            io_writes_data = json.load(io_writes_file)['data']['result']
        with open(f'./{experiment_folder}/prometheus_mem_utilisation.json', 'r') as mem_utilisation_file:
            mem_utilisation_data = json.load(mem_utilisation_file)['data']['result']
        with open(f'./{experiment_folder}/prometheus_network_transmit.json', 'r') as network_transmit_file:
            network_transmit_data = json.load(network_transmit_file)['data']['result']
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
    io_writes = {}
    mem_utilisation = services.copy()
    network_transmit = {}

    fig, ax = plt.subplots(6, 1, figsize=(10, 12))

    """
    PROCESS CPU UTILISATION
    """
    cpu_utilisation = {}
    for result in cpu_utilisation_data:
        values = result['values']
        service_name = get_name(result['metric']['pod'])
        values_dict = {}

        if service_name in cpu_utilisation.keys():
            values_dict = cpu_utilisation[service_name]

        for value in values:
            timestamp = int(value[0])
            utilisation = float(value[1])

            if timestamp in values_dict.keys():
                values_dict[timestamp] += utilisation
            else:
                values_dict[timestamp] = utilisation
        
        cpu_utilisation[service_name] = values_dict

    # get start time for the experiment
    start_time = None
    for service_name, values_dict in cpu_utilisation.items():
        for timestamp in values_dict.keys():
            if start_time is None:
                start_time = timestamp
            elif start_time > timestamp:
                start_time = timestamp


    # move timestamp relative to 0-3600
    new_data = {}
    for service_name, values_dict in cpu_utilisation.items():
        for timestamp, value in values_dict.items():
            if service_name not in new_data:
                new_data[service_name] = {}
            new_data[service_name][timestamp - start_time] = value

    cpu_utilisation = new_data
    for service_name, values_dict in cpu_utilisation.items():
        if service_name == 'compose-post-service':
            # sort dict based on timestamp
            ordered_data = dict(sorted(values_dict.items()))

            times = list(ordered_data.keys())
            values = list(ordered_data.values())
            
            ax[0].plot(times, values)
            ax[0].axvline(1800, color='r', linestyle='--')
            ax[0].set_ylabel('CPU Use (Cores)')
            ax[0].set_xlabel('Time (s)')

    """
    PROCESS CPU THROTTLING
    """
    cpu_throttling = {}
    for result in cpu_throttling_data:
        values = result['values']
        service_name = get_name(result['metric']['pod'])
        values_dict = {}

        if service_name in cpu_throttling.keys():
            values_dict = cpu_throttling[service_name]

        for value in values:
            timestamp = int(value[0] - start_time)
            throttling = float(value[1])

            if timestamp in values_dict.keys():
                values_dict[timestamp] += throttling
            else:
                values_dict[timestamp] = throttling
        
        cpu_throttling[service_name] = values_dict

    for service_name, values_dict in cpu_throttling.items():
        if service_name == 'compose-post-service':
            # sort dict based on timestamp
            ordered_data = dict(sorted(values_dict.items()))

            times = list(ordered_data.keys())
            values = list(ordered_data.values())
            
            ax[1].plot(times, values)
            ax[1].axvline(1800, color='r', linestyle='--')
            ax[1].set_ylabel('CPU Throttling (%))')
            ax[1].set_ylim(0, 1)
            ax[1].set_xlabel('Time (s)')

    """
    PROCESS INSTANCE COUNT
    """
    instance_count = {}
    for result in instance_count_data:
        values = result['values']
        service_name = get_name(result['metric']['pod'])
        values_dict = {}

        if service_name in instance_count.keys():
            values_dict = instance_count[service_name]

        for value in values:
            timestamp = int(value[0] - start_time)
            instances = float(value[1])

            if timestamp in values_dict.keys():
                values_dict[timestamp] += instances
            else:
                values_dict[timestamp] = instances
        
        instance_count[service_name] = values_dict
        
    for servicename, time_data in instance_count.items():        
        if servicename=='compose-post-service':
            # sort dict based on timestamp
            ordered_data = dict(sorted(values_dict.items()))

            times = list(ordered_data.keys())
            values = list(ordered_data.values())
            
            ax[2].plot(times, values)
            ax[2].axvline(1800, color='r', linestyle='--')
            ax[2].set_ylabel('Instance Count')
            ax[2].set_ylim(0, 10)
            ax[2].set_yticks(range(1, 10, 2))
            ax[2].set_xlabel('Time (s)')

    """
    PROCESS IO WRITES
    """
    for result in io_writes_data:
        for values in result["values"]:
            time = int(values[0] - start_time)
            value = float(values[1])

            if time not in io_writes.keys():
                io_writes[time] = value
            else:
                io_writes[time] += value

    times = list(io_writes.keys())
    values = list(io_writes.values())

    ax[3].plot(times, values)
    ax[3].axvline(1800, color='r', linestyle='--')
    ax[3].set_ylabel('IO Writes (Bytes)')
    ax[3].set_xlabel('Time (s)')

    """
    PROCESS MEMORY UTILISATION
    """
    mem_utilisation = {}
    for result in mem_utilisation_data:
        values = result['values']
        service_name = get_name(result['metric']['pod'])
        values_dict = {}

        if service_name in mem_utilisation.keys():
            values_dict = mem_utilisation[service_name]

        for value in values:
            timestamp = int(value[0] - start_time)
            utilisation = float(value[1])

            if timestamp in values_dict.keys():
                values_dict[timestamp] += utilisation
            else:
                values_dict[timestamp] = utilisation
        
        mem_utilisation[service_name] = values_dict

    
    for service_name, values_dict in mem_utilisation.items():
        if service_name == 'compose-post-service':
            # sort dict based on timestamp
            ordered_data = dict(sorted(values_dict.items()))

            times = list(ordered_data.keys())
            values = list(ordered_data.values())
            
            ax[4].plot(times, values)
            ax[4].axvline(1800, color='r', linestyle='--')
            ax[4].set_ylabel('Mem Use (Bytes))')
            ax[4].set_xlabel('Time (s)')

    """
    PROCESS NETWORK TRANSMITS
    """
    for result in network_transmit_data:
        for values in result["values"]:
            time = int(values[0] - start_time)
            value = float(values[1])

            if time not in network_transmit.keys():
                network_transmit[time] = value
            else:
                network_transmit[time] += value

    times = list(network_transmit.keys())
    values = list(network_transmit.values())

    ax[5].plot(times, values)
    ax[5].axvline(1800, color='r', linestyle='--')
    ax[5].set_ylabel('Network Transmits (Bytes)')
    ax[5].set_xlabel('Time (s)')

    plt.savefig(f'{sys.argv[1]}.png')


if __name__ == "__main__":
    main()
