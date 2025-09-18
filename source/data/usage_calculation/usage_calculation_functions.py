
def estimate_electricity_usage_kwh(cpu_seconds_total, cpu_tdp_w):
    # Calculate the usage in kWh
    usage_kwh = cpu_seconds_total * cpu_tdp_w / 1000
    return usage_kwh

def estimate_carbon_footprint_gCO2eq(usage_kwh, ci_g_per_kwh):
    # Calculate the carbon footprint in gCO2eq
    carbon_footprint_gCO2eq = usage_kwh * ci_g_per_kwh
    return carbon_footprint_gCO2eq
