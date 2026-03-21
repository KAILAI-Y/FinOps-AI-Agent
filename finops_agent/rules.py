from finops_agent.schema import Recommendation, VMMetric


LOW_CPU_THRESHOLD = 10.0
IDLE_CPU_THRESHOLD = 3.0
HIGH_CPU_THRESHOLD = 80.0
HIGH_MEMORY_THRESHOLD = 85.0
HIGH_NETWORK_TOTAL_THRESHOLD = 500 * 1024 * 1024
HIGH_DISK_TOTAL_THRESHOLD = 2 * 1024 * 1024 * 1024
LONG_LIVED_RUNNING_HOURS_THRESHOLD = 24 * 30
REQUIRED_LABELS = ("env", "owner", "team", "cost-center")
PERSISTENT_LOW_UTILIZATION_DAYS_THRESHOLD = 3


def build_recommendations(metrics: list[VMMetric]) -> list[Recommendation]:
    recommendations: list[Recommendation] = []
    for metric in metrics:
        recommendations.extend(_recommend_for_vm(metric))
    return recommendations


def build_recommendation(
    metric: VMMetric,
    domain: str,
    category: str,
    severity: str,
    summary: str,
    rationale: str,
    suggested_action: str,
    estimated_savings_hint: str,
) -> Recommendation:
    return Recommendation(
        instance_name=metric.instance_name,
        domain=domain,
        category=category,
        severity=severity,
        action_priority=resolve_action_priority(domain, severity),
        needs_human_review=resolve_needs_human_review(domain, category, severity),
        recommended_owner=resolve_recommended_owner(metric, domain),
        summary=summary,
        rationale=rationale,
        suggested_action=suggested_action,
        estimated_savings_hint=estimated_savings_hint,
    )


def resolve_action_priority(domain: str, severity: str) -> str:
    if severity == "high":
        return "p1"
    if domain == "sre" and severity == "medium":
        return "p2"
    if severity == "medium":
        return "p3"
    return "p4"


def resolve_needs_human_review(domain: str, category: str, severity: str) -> bool:
    if domain == "sre":
        return True
    if category in {
        "idle-instance",
        "rightsizing",
        "persistent-low-utilization",
        "idle-but-expensive",
        "lifecycle",
    }:
        return True
    return severity != "low"


def resolve_recommended_owner(metric: VMMetric, domain: str) -> str:
    labels = metric.labels or {}
    if domain == "governance":
        return labels.get("owner") or labels.get("team") or "platform-team"
    if domain == "sre":
        return labels.get("team") or labels.get("owner") or "sre-team"
    return labels.get("owner") or labels.get("team") or "finops-team"


def _recommend_for_vm(metric: VMMetric) -> list[Recommendation]:
    findings: list[Recommendation] = []

    cpu = metric.cpu_utilization_avg
    memory = metric.memory_utilization_avg
    seven_day_avg_cpu = metric.seven_day_avg_cpu
    seven_day_low_utilization_days = metric.seven_day_low_utilization_days or 0
    network_total = (metric.network_in_bytes_1h or 0) + (metric.network_out_bytes_1h or 0)
    disk_total = (metric.disk_read_bytes_1h or 0) + (metric.disk_write_bytes_1h or 0)
    low_activity = network_total < 50 * 1024 * 1024 and disk_total < 100 * 1024 * 1024
    low_memory = memory is None or memory <= 35.0
    low_cpu = cpu is not None and cpu <= LOW_CPU_THRESHOLD
    idle_cpu = cpu is not None and cpu <= IDLE_CPU_THRESHOLD
    high_cpu = cpu is not None and cpu >= HIGH_CPU_THRESHOLD
    high_memory = memory is not None and memory >= HIGH_MEMORY_THRESHOLD
    high_io_with_low_cpu = low_cpu and not low_activity
    memory_bound = memory is not None and low_cpu and memory >= 70.0
    is_running = metric.status.upper() == "RUNNING"
    high_network = network_total >= HIGH_NETWORK_TOTAL_THRESHOLD
    high_disk = disk_total >= HIGH_DISK_TOTAL_THRESHOLD
    long_lived_running = (
        is_running
        and metric.instance_age_hours is not None
        and metric.instance_age_hours >= LONG_LIVED_RUNNING_HOURS_THRESHOLD
    )

    if is_running and cpu is None:
        findings.append(
            build_recommendation(
                metric=metric,
                domain="sre",
                category="missing-observability",
                severity="high",
                summary="Running instance is missing CPU telemetry.",
                rationale=(
                    "The VM is in RUNNING state but no CPU utilization data was collected for the current lookback window."
                ),
                suggested_action="Verify Cloud Monitoring coverage, IAM access, and agent or metric availability before relying on this instance for operational decisions.",
                estimated_savings_hint="Operational visibility gap; no direct savings estimate.",
            )
        )

    if is_running and memory is None:
        findings.append(
            build_recommendation(
                metric=metric,
                domain="sre",
                category="missing-observability",
                severity="medium",
                summary="Running instance is missing memory telemetry.",
                rationale=(
                    "The VM is in RUNNING state but no memory utilization data was collected for the current lookback window."
                ),
                suggested_action="Confirm memory metrics are available through the Ops Agent or equivalent monitoring path.",
                estimated_savings_hint="Operational visibility gap; no direct savings estimate.",
            )
        )

    if is_running and high_cpu:
        findings.append(
            build_recommendation(
                metric=metric,
                domain="sre",
                category="high-cpu-sustained",
                severity="high",
                summary="Instance is operating at high CPU utilization.",
                rationale=(
                    f"Average CPU utilization over the last hour is {cpu}%, which is at or above the high-utilization threshold of {HIGH_CPU_THRESHOLD}%."
                ),
                suggested_action="Inspect workload demand, autoscaling behavior, and recent deploys before the instance becomes CPU-constrained.",
                estimated_savings_hint="Reliability risk; prioritize stability review over cost optimization.",
            )
        )

    if is_running and high_memory:
        findings.append(
            build_recommendation(
                metric=metric,
                domain="sre",
                category="high-memory-pressure",
                severity="high",
                summary="Instance is operating with high memory utilization.",
                rationale=(
                    f"Average memory utilization over the last hour is {memory}%, which is at or above the pressure threshold of {HIGH_MEMORY_THRESHOLD}%."
                ),
                suggested_action="Review resident memory growth, workload concurrency, and reclaim behavior before memory pressure affects service health.",
                estimated_savings_hint="Reliability risk; avoid downsizing and investigate capacity needs.",
            )
        )

    if is_running and high_network:
        findings.append(
            build_recommendation(
                metric=metric,
                domain="sre",
                category="high-network-throughput",
                severity="medium",
                summary="Instance is handling high recent network throughput.",
                rationale=(
                    f"Combined network traffic over the last hour is {round(network_total / (1024 * 1024), 1)} MB, "
                    f"which is above the review threshold of {round(HIGH_NETWORK_TOTAL_THRESHOLD / (1024 * 1024), 1)} MB."
                ),
                suggested_action="Review traffic patterns, service role, and scaling posture before applying disruptive changes.",
                estimated_savings_hint="Operational caution signal; validate workload criticality before optimization changes.",
            )
        )

    if is_running and high_disk:
        findings.append(
            build_recommendation(
                metric=metric,
                domain="sre",
                category="high-disk-activity",
                severity="medium",
                summary="Instance shows high recent disk activity.",
                rationale=(
                    f"Combined disk read/write activity over the last hour is {round(disk_total / (1024 * 1024 * 1024), 2)} GB, "
                    f"which is above the review threshold of {round(HIGH_DISK_TOTAL_THRESHOLD / (1024 * 1024 * 1024), 2)} GB."
                ),
                suggested_action="Inspect storage-heavy workload behavior before changing machine size, storage class, or runtime schedule.",
                estimated_savings_hint="Operational caution signal; I/O-heavy workloads can be sensitive to premature optimization.",
            )
        )

    if long_lived_running:
        findings.append(
            build_recommendation(
                metric=metric,
                domain="sre",
                category="long-lived-running-instance",
                severity="medium",
                summary="Running instance has remained in service for a long period.",
                rationale=(
                    f"Instance age is approximately {round(metric.instance_age_hours, 1)} hours while still in RUNNING state."
                ),
                suggested_action="Review patch posture, service ownership, and restart tolerance for this long-lived instance.",
                estimated_savings_hint="Stability and governance review signal; long-lived workloads deserve periodic operational review.",
            )
        )

    if idle_cpu and low_activity and low_memory:
        findings.append(
            build_recommendation(
                metric=metric,
                domain="finops",
                category="idle-instance",
                severity="high",
                summary="Instance appears mostly idle.",
                rationale=(
                    f"Average CPU utilization over the last hour is {cpu}%, which is below "
                    f"the idle threshold of {IDLE_CPU_THRESHOLD}%, with low disk/network activity "
                    f"and memory usage at {memory}%."
                    if memory is not None
                    else f"the idle threshold of {IDLE_CPU_THRESHOLD}%, with low disk and network activity."
                ),
                suggested_action="Validate business ownership and consider stop scheduling or downsizing.",
                estimated_savings_hint=(
                    f"High potential savings if the VM can be stopped outside business hours. "
                    f"Estimated monthly run cost: ${metric.estimated_monthly_cost}."
                    if metric.estimated_monthly_cost is not None
                    else "High potential savings if the VM can be stopped outside business hours."
                ),
            )
        )
    elif low_cpu and not high_io_with_low_cpu and not memory_bound:
        findings.append(
            build_recommendation(
                metric=metric,
                domain="finops",
                category="rightsizing",
                severity="medium",
                summary="Instance may be oversized for current workload.",
                rationale=(
                    f"Average CPU utilization over the last hour is {cpu}%, which is below "
                    f"the low-utilization threshold of {LOW_CPU_THRESHOLD}%."
                    if memory is None
                    else f"Average CPU utilization is {cpu}% and memory utilization is {memory}%, "
                    f"suggesting the VM may be oversized."
                ),
                suggested_action="Review historical peaks and evaluate a smaller machine type.",
                estimated_savings_hint=(
                    f"Moderate savings likely if the machine family or size can be reduced. "
                    f"Estimated monthly run cost: ${metric.estimated_monthly_cost}."
                    if metric.estimated_monthly_cost is not None
                    else "Moderate savings likely if the machine family or size can be reduced."
                ),
            )
        )

    if high_io_with_low_cpu:
        findings.append(
            build_recommendation(
                metric=metric,
                domain="sre",
                category="review-before-rightsizing",
                severity="medium",
                summary="Low CPU but meaningful I/O activity detected.",
                rationale=(
                    "CPU usage is low, but disk or network throughput is still material. "
                    "This can indicate a throughput-bound workload rather than an oversized VM."
                ),
                suggested_action="Review disk and network patterns before applying a smaller machine type.",
                estimated_savings_hint="Avoid premature downsizing that could degrade storage or network-heavy workloads.",
            )
        )

    if memory_bound:
        findings.append(
            build_recommendation(
                metric=metric,
                domain="sre",
                category="memory-bound",
                severity="medium",
                summary="CPU is low but memory usage is relatively high.",
                rationale=(
                    f"Average CPU utilization is {cpu}%, while memory utilization is {memory}%. "
                    "This suggests the workload may be memory-constrained rather than oversized."
                ),
                suggested_action="Check memory pressure and avoid downsizing to a smaller memory footprint.",
                estimated_savings_hint="Avoid cost-saving actions that would create memory contention.",
            )
        )

    missing_labels = [label for label in REQUIRED_LABELS if label not in metric.labels]
    if missing_labels:
        findings.append(
            build_recommendation(
                metric=metric,
                domain="governance",
                category="governance",
                severity="medium",
                summary="Instance is missing FinOps ownership labels.",
                rationale=(
                    "Missing labels make chargeback and optimization routing harder. "
                    f"Missing: {', '.join(missing_labels)}."
                ),
                suggested_action="Populate ownership and environment labels in the instance metadata.",
                estimated_savings_hint="Indirect savings by improving accountability and remediation speed.",
            )
        )

    if metric.estimated_monthly_cost is not None and metric.estimated_monthly_cost >= 50:
        findings.append(
            build_recommendation(
                metric=metric,
                domain="finops",
                category="cost-awareness",
                severity="low",
                summary="Instance has a non-trivial estimated monthly run cost.",
                rationale=(
                    f"Estimated monthly run cost is ${metric.estimated_monthly_cost} based on machine "
                    f"type {metric.machine_type} in {metric.zone}."
                ),
                suggested_action="Prioritize this instance for review when optimization opportunities appear.",
                estimated_savings_hint="Higher-value candidates should be reviewed first to maximize FinOps impact.",
            )
        )

    if (
        seven_day_avg_cpu is not None
        and seven_day_low_utilization_days >= PERSISTENT_LOW_UTILIZATION_DAYS_THRESHOLD
        and low_cpu
    ):
        findings.append(
            build_recommendation(
                metric=metric,
                domain="finops",
                category="persistent-low-utilization",
                severity="medium",
                summary="Instance has remained underutilized across multiple recent days.",
                rationale=(
                    f"Average CPU over the last 7 days is {seven_day_avg_cpu}% and the VM stayed "
                    f"at or below {LOW_CPU_THRESHOLD}% CPU on {seven_day_low_utilization_days} day(s)."
                ),
                suggested_action="Review whether this workload needs always-on capacity or can be downsized after validating historical peaks.",
                estimated_savings_hint="Persistent underutilization is a stronger optimization signal than a single low-usage snapshot.",
            )
        )

    if metric.idle_but_expensive_flag:
        findings.append(
            build_recommendation(
                metric=metric,
                domain="finops",
                category="idle-but-expensive",
                severity="high",
                summary="Instance is both persistently underutilized and relatively expensive.",
                rationale=(
                    "Historical data suggests the VM stays underutilized across recent days while "
                    "its estimated monthly cost remains high enough to justify priority review."
                ),
                suggested_action="Prioritize this instance for owner validation, schedule review, or rightsizing analysis.",
                estimated_savings_hint="This combination often represents a higher-value savings opportunity than low-utilization alone.",
            )
        )

    if (
        metric.instance_age_hours is not None
        and metric.instance_age_hours > LONG_LIVED_RUNNING_HOURS_THRESHOLD
        and low_cpu
        and not high_io_with_low_cpu
        and not memory_bound
    ):
        findings.append(
            build_recommendation(
                metric=metric,
                domain="finops",
                category="stale-capacity",
                severity="medium",
                summary="Long-lived instance with consistently low recent utilization.",
                rationale=(
                    f"Instance age is approximately {round(metric.instance_age_hours, 1)} hours and "
                    f"recent average CPU utilization is only {cpu}%."
                ),
                suggested_action="Confirm whether the workload still needs always-on capacity or can move to scheduled runtime.",
                estimated_savings_hint="Potential savings if the workload can be consolidated or stopped on a schedule.",
            )
        )

    if not is_running:
        findings.append(
            build_recommendation(
                metric=metric,
                domain="finops",
                category="lifecycle",
                severity="low",
                summary="Instance is not in RUNNING state.",
                rationale=(
                    f"Current instance status is {metric.status}. Non-running resources may still "
                    "have attached disks or reserved IPs that incur cost."
                ),
                suggested_action="Review attached resources and remove unused storage or reservations.",
                estimated_savings_hint="Low to moderate savings depending on attached resources.",
            )
        )

    return findings
