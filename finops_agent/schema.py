from dataclasses import asdict, dataclass, field


@dataclass
class VMMetric:
    instance_name: str
    machine_type: str
    zone: str
    instance_id: str
    status: str
    labels: dict[str, str] = field(default_factory=dict)
    creation_timestamp: str = ""
    cpu_utilization_avg: float | None = None
    memory_utilization_avg: float | None = None
    disk_read_bytes_1h: float | None = None
    disk_write_bytes_1h: float | None = None
    network_in_bytes_1h: float | None = None
    network_out_bytes_1h: float | None = None
    instance_age_hours: float | None = None
    uptime_total_seconds: float | None = None
    estimated_hourly_cost: float | None = None
    estimated_monthly_cost: float | None = None
    seven_day_avg_cpu: float | None = None
    seven_day_low_utilization_days: int | None = None
    idle_but_expensive_flag: bool = False
    timestamp: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Recommendation:
    instance_name: str
    domain: str
    category: str
    severity: str
    action_priority: str
    needs_human_review: bool
    recommended_owner: str
    summary: str
    rationale: str
    suggested_action: str
    estimated_savings_hint: str

    def to_dict(self) -> dict:
        return asdict(self)
