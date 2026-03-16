REGION_MULTIPLIER = {
    "us-central1": 1.0,
    "us-east1": 1.0,
    "us-west1": 1.02,
    "northamerica-northeast1": 1.05,
    "europe-west1": 1.08,
    "asia-east1": 1.12,
}


MACHINE_TYPE_BASE_HOURLY_USD = {
    "e2-micro": 0.0084,
    "e2-small": 0.0167,
    "e2-medium": 0.0334,
    "e2-standard-2": 0.0670,
    "e2-standard-4": 0.1340,
    "n2-standard-2": 0.0971,
    "n2-standard-4": 0.1942,
}


def zone_to_region(zone):
    return "-".join(zone.split("-")[:-1]) if zone else ""


def estimate_hourly_cost(machine_type, zone):
    base_cost = MACHINE_TYPE_BASE_HOURLY_USD.get(machine_type)
    if base_cost is None:
        return None

    region = zone_to_region(zone)
    multiplier = REGION_MULTIPLIER.get(region, 1.0)
    return round(base_cost * multiplier, 4)


def estimate_monthly_cost(machine_type, zone, hours_per_month=730):
    hourly_cost = estimate_hourly_cost(machine_type, zone)
    if hourly_cost is None:
        return None
    return round(hourly_cost * hours_per_month, 2)
