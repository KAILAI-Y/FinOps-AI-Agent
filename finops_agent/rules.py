from finops_agent.schema import Recommendation, VMMetric


LOW_CPU_THRESHOLD = 10.0
IDLE_CPU_THRESHOLD = 3.0
REQUIRED_LABELS = ("env", "owner", "team", "cost-center")


def build_recommendations(metrics: list[VMMetric]) -> list[Recommendation]:
    recommendations: list[Recommendation] = []
    for metric in metrics:
        recommendations.extend(_recommend_for_vm(metric))
    return recommendations


def _recommend_for_vm(metric: VMMetric) -> list[Recommendation]:
    findings: list[Recommendation] = []

    cpu = metric.cpu_utilization_avg
    memory = metric.memory_utilization_avg
    network_total = (metric.network_in_bytes_1h or 0) + (metric.network_out_bytes_1h or 0)
    disk_total = (metric.disk_read_bytes_1h or 0) + (metric.disk_write_bytes_1h or 0)
    low_activity = network_total < 50 * 1024 * 1024 and disk_total < 100 * 1024 * 1024
    low_memory = memory is None or memory <= 35.0
    low_cpu = cpu is not None and cpu <= LOW_CPU_THRESHOLD
    idle_cpu = cpu is not None and cpu <= IDLE_CPU_THRESHOLD
    high_io_with_low_cpu = low_cpu and not low_activity
    memory_bound = memory is not None and low_cpu and memory >= 70.0

    if idle_cpu and low_activity and low_memory:
        findings.append(
            Recommendation(
                instance_name=metric.instance_name,
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
            Recommendation(
                instance_name=metric.instance_name,
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
            Recommendation(
                instance_name=metric.instance_name,
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
            Recommendation(
                instance_name=metric.instance_name,
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
            Recommendation(
                instance_name=metric.instance_name,
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
            Recommendation(
                instance_name=metric.instance_name,
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
        metric.instance_age_hours is not None
        and metric.instance_age_hours > 24 * 30
        and low_cpu
        and not high_io_with_low_cpu
        and not memory_bound
    ):
        findings.append(
            Recommendation(
                instance_name=metric.instance_name,
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

    if metric.status.upper() != "RUNNING":
        findings.append(
            Recommendation(
                instance_name=metric.instance_name,
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
