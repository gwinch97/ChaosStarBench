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
    io_writes = {}
    mem_utilisation = services.copy()
    network_transmit = {}

    fig, ax = plt.subplots(6, 1, figsize=(10, 12))

    """
    PROCESS CPU UTILISATION
    """
    start_time = cpu_utilisation_data["data"]["result"][0]["values"][0][0]

    service_info = {}
    for result in cpu_utilisation_data['data']['result']:
        ms_name = get_name(result['metric']['pod'])
        if ms_name in service_info.keys():
            service_info[ms_name].append(result)
        else:
            service_info[ms_name] = [result]

    for instance_info in service_info.values():
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
            
            ax[0].plot(times, values)
            ax[0].axvline(1800, color='r', linestyle='--')
            ax[0].set_ylabel('CPU Use (Cores)')
            ax[0].set_xlabel('Time (s)')

    """
    PROCESS CPU THROTTLING
    """
    start_time = cpu_throttling_data["data"]["result"][0]["values"][0][0]

    for result in cpu_throttling_data['data']['result']:
        ms_name = get_name(result['metric']['pod'])
        if ms_name in service_info.keys():
            service_info[ms_name].append(result)
        else:
            service_info[ms_name] = [result]

    for instance_info in service_info.values():
        for instance in instance_info:
            for timestep in instance['values']:
                time = int(timestep[0] - start_time)
                value = float(timestep[1])
                ms_name = get_name(instance['metric']['pod'])
                
                if time not in cpu_throttling[ms_name]:
                    cpu_throttling[ms_name][time] = value
                else:
                    cpu_throttling[ms_name][time] = (cpu_throttling[ms_name][time] + value) / 2

    for servicename, time_data in cpu_throttling.items():
        if servicename=='compose-post-service':
            times = list(time_data.keys())
            values = list(time_data.values())
            
            ax[1].plot(times, values)
            ax[1].axvline(1800, color='r', linestyle='--')
            ax[1].set_ylabel('CPU Throttling (%)')
            ax[1].set_xlabel('Time (s)')

    """
    PROCESS INSTANCE COUNT
    """

    """
    PROCESS IO WRITES
    """
    start_time = io_writes_data["data"]["result"][0]["values"][0][0]

    for result in io_writes_data["data"]["result"]:
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

    plt.tight_layout()
    plt.savefig(f'{sys.argv[1]}.png')

    """
    PROCESS MEMORY UTILISATION
    """
    start_time =  mem_utilisation_data["data"]["result"][0]["values"][0][0]

    service_info = {}
    for result in mem_utilisation_data['data']['result']:
        ms_name = get_name(result['metric']['pod'])
        if ms_name in service_info.keys():
            service_info[ms_name].append(result)
        else:
            service_info[ms_name] = [result]

    for instance_info in service_info.values():
        for instance in instance_info:
            start_time = instance['values'][0][0]
            for timestep in instance['values']:
                time = int(timestep[0] - start_time)
                value = float(timestep[1])
                ms_name = get_name(instance['metric']['pod'])
                
                if time not in mem_utilisation[ms_name]:
                    mem_utilisation[ms_name][time] = value
                else:
                    mem_utilisation[ms_name][time] = (mem_utilisation[ms_name][time] + value) / 2

    for servicename, time_data in mem_utilisation.items():
        if servicename=='compose-post-service':
            times = list(time_data.keys())
            values = list(time_data.values())
            
            ax[4].plot(times, values)
            ax[4].axvline(1800, color='r', linestyle='--')
            ax[4].set_ylabel('Mem Use (Bytes)')
            ax[4].set_xlabel('Time (s)')

    """
    PROCESS NETWORK TRANSMITS
    """
    start_time = network_transmit_data["data"]["result"][0]["values"][0][0]

    for result in network_transmit_data["data"]["result"]:
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
