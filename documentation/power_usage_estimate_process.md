
## TDP Calculation


## Backup calculation:
    First, we need to determine how hard the CPU is working. We do this by measuring how much time it's not doing anything.

    node_cpu_seconds_total{mode="idle"}

    This is a counter from Prometheus that continuously records the total number of seconds the CPU has been in an "idle" state.

    Formula to get Idle Rate:
    rate(node_cpu_seconds_total{mode="idle"}[5m])

    The rate() function calculates the per-second average of how fast the idle time is increasing over the last 5 minutes. 

    Formula for "Busy" Percentage:
    CPU Busy % = 1 - (Idle Rate)

    If the CPU was 80% idle, it must have been 20% busy.

    Next, we estimate the server's power consumption in Watts based on how busy the CPU is. 

    A server uses a baseline amount of power when idle and ramps up to a maximum power level when under full load.


    CPU_POWER_IDLE: The estimated power draw in Watts when the CPU is 0% busy (e.g., 50W).

    CPU_POWER_MAX: The estimated power draw in Watts when the CPU is 100% busy (e.g., 250W).

    Estimated Watts = (CPU_POWER_MAX - CPU_POWER_IDLE) * (CPU Busy %) + CPU_POWER_IDLE

    This formula scales the power draw between the idle and max values. For example, if the CPU is 20% busy, the power draw would be: (250W - 50W) * 0.20 + 50W = 90 Watts.

    Total Joules = Estimated Watts × 1800 seconds 

    Total kWh = Total Joules / 3,600,000 (3.6 million Joules in 1 kWh)
