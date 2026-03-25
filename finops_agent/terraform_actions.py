import json
from dataclasses import asdict, dataclass
from pathlib import Path

from finops_agent.schema import Recommendation, VMMetric


RIGHTSIZING_CATEGORIES = {
    "rightsizing",
    "persistent-low-utilization",
    "idle-but-expensive",
    "idle-instance",
}
BLOCKING_CATEGORIES = {
    "review-before-rightsizing",
    "memory-bound",
    "high-cpu-sustained",
    "high-memory-pressure",
    "high-network-throughput",
    "high-disk-activity",
    "missing-observability",
}
SRE_CATEGORIES = BLOCKING_CATEGORIES | {"long-lived-running-instance"}
GOVERNANCE_CATEGORIES = {"governance"}
MACHINE_TYPE_DOWNSIZE_MAP = {
    "e2-standard-8": "e2-standard-4",
    "e2-standard-4": "e2-standard-2",
    "e2-standard-2": "e2-medium",
    "e2-highmem-8": "e2-highmem-4",
    "e2-highmem-4": "e2-highmem-2",
    "e2-highcpu-8": "e2-highcpu-4",
    "e2-highcpu-4": "e2-highcpu-2",
    "e2-medium": "e2-small",
    "e2-small": "e2-micro",
}
VM_METRIC_FIELDS = set(VMMetric.__dataclass_fields__.keys())
RECOMMENDATION_FIELDS = set(Recommendation.__dataclass_fields__.keys())


@dataclass
class TerraformAction:
    instance_name: str
    resource_address: str
    change_type: str
    tfvars_key: str
    current_value: str
    proposed_value: str
    recommendation_category: str
    action_priority: str
    recommended_owner: str
    needs_human_review: bool
    summary: str
    rationale: str
    suggested_action: str
    estimated_savings_hint: str
    tfvars_patch: str

    def to_dict(self) -> dict:
        return asdict(self)


def load_tfvars(tfvars_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not tfvars_path.is_file():
        return values

    for raw_line in tfvars_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_metrics(metrics_path: Path) -> list[VMMetric]:
    payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    return [VMMetric(**_filter_payload(item, VM_METRIC_FIELDS)) for item in payload]


def load_recommendations(recommendations_path: Path) -> list[Recommendation]:
    payload = json.loads(recommendations_path.read_text(encoding="utf-8"))
    return [normalize_recommendation(item) for item in payload]


def _filter_payload(item: dict, allowed_fields: set[str]) -> dict:
    return {key: value for key, value in item.items() if key in allowed_fields}


def normalize_recommendation(item: dict) -> Recommendation:
    filtered = _filter_payload(item, RECOMMENDATION_FIELDS)
    if set(filtered.keys()) == RECOMMENDATION_FIELDS:
        return Recommendation(**filtered)

    category = item.get("category", "unknown")
    domain = item.get("domain")
    if not domain:
        if category in SRE_CATEGORIES:
            domain = "sre"
        elif category in GOVERNANCE_CATEGORIES:
            domain = "governance"
        else:
            domain = "finops"

    severity = item.get("severity", "unknown")
    action_priority = item.get("action_priority")
    if not action_priority:
        if severity == "high":
            action_priority = "p1"
        elif domain == "sre" and severity == "medium":
            action_priority = "p2"
        elif severity == "medium":
            action_priority = "p3"
        else:
            action_priority = "p4"

    needs_human_review = item.get("needs_human_review")
    if needs_human_review is None:
        needs_human_review = severity != "low" or domain == "sre"

    return Recommendation(
        instance_name=item.get("instance_name", "unknown"),
        domain=domain,
        category=category,
        severity=severity,
        action_priority=action_priority,
        needs_human_review=needs_human_review,
        recommended_owner=item.get("recommended_owner", "unknown"),
        summary=item.get("summary", ""),
        rationale=item.get("rationale", ""),
        suggested_action=item.get("suggested_action", ""),
        estimated_savings_hint=item.get("estimated_savings_hint", ""),
    )


def generate_terraform_actions(
    metrics: list[VMMetric],
    recommendations: list[Recommendation],
    tfvars: dict[str, str],
) -> dict:
    metric_by_name = {metric.instance_name: metric for metric in metrics}
    recommendations_by_instance: dict[str, list[Recommendation]] = {}
    for recommendation in recommendations:
        recommendations_by_instance.setdefault(recommendation.instance_name, []).append(recommendation)

    configured_instance_name = tfvars.get("instance_name")
    configured_machine_type = tfvars.get("machine_type")
    actions: list[TerraformAction] = []
    skipped: list[dict] = []

    for instance_name, instance_recommendations in recommendations_by_instance.items():
        metric = metric_by_name.get(instance_name)
        if metric is None:
            skipped.append({"instance_name": instance_name, "reason": "No matching metric payload found."})
            continue

        if configured_instance_name and instance_name != configured_instance_name:
            skipped.append(
                {
                    "instance_name": instance_name,
                    "reason": "Instance does not match the Terraform-managed instance_name in terraform.tfvars.",
                }
            )
            continue

        if metric.labels.get("managed_by") not in {"terraform", "Terraform"}:
            skipped.append(
                {
                    "instance_name": instance_name,
                    "reason": "Instance is not marked with managed_by=terraform.",
                }
            )
            continue

        categories = {recommendation.category for recommendation in instance_recommendations}
        if not (categories & RIGHTSIZING_CATEGORIES):
            skipped.append(
                {
                    "instance_name": instance_name,
                    "reason": "No right-sizing recommendation category is present for this instance.",
                }
            )
            continue

        blocking_categories = sorted(categories & BLOCKING_CATEGORIES)
        if blocking_categories:
            skipped.append(
                {
                    "instance_name": instance_name,
                    "reason": f"Blocked by conflicting SRE findings: {', '.join(blocking_categories)}.",
                }
            )
            continue

        current_machine_type = configured_machine_type or metric.machine_type
        proposed_machine_type = MACHINE_TYPE_DOWNSIZE_MAP.get(current_machine_type)
        if proposed_machine_type is None:
            skipped.append(
                {
                    "instance_name": instance_name,
                    "reason": f"No supported downsize mapping exists for machine type {current_machine_type}.",
                }
            )
            continue

        selected_recommendation = select_primary_rightsizing_recommendation(instance_recommendations)
        actions.append(
            TerraformAction(
                instance_name=instance_name,
                resource_address="google_compute_instance.demo_vm",
                change_type="update",
                tfvars_key="machine_type",
                current_value=current_machine_type,
                proposed_value=proposed_machine_type,
                recommendation_category=selected_recommendation.category,
                action_priority=selected_recommendation.action_priority,
                recommended_owner=selected_recommendation.recommended_owner,
                needs_human_review=selected_recommendation.needs_human_review,
                summary=f"Change Terraform machine_type from {current_machine_type} to {proposed_machine_type}.",
                rationale=selected_recommendation.rationale,
                suggested_action=selected_recommendation.suggested_action,
                estimated_savings_hint=selected_recommendation.estimated_savings_hint,
                tfvars_patch=build_tfvars_patch(
                    tfvars_key="machine_type",
                    current_value=current_machine_type,
                    proposed_value=proposed_machine_type,
                ),
            )
        )

    combined_patch = "\n\n".join(action.tfvars_patch for action in actions)
    return {
        "summary": {
            "managed_instance_name": configured_instance_name or "",
            "candidate_instances": len(recommendations_by_instance),
            "proposed_actions": len(actions),
            "skipped_instances": len(skipped),
        },
        "actions": [action.to_dict() for action in actions],
        "tfvars_patch_preview": combined_patch,
        "skipped": skipped,
    }


def select_primary_rightsizing_recommendation(
    recommendations: list[Recommendation],
) -> Recommendation:
    eligible = [recommendation for recommendation in recommendations if recommendation.category in RIGHTSIZING_CATEGORIES]
    priority_rank = {"p1": 1, "p2": 2, "p3": 3, "p4": 4}
    return sorted(
        eligible,
        key=lambda item: (
            priority_rank.get(item.action_priority, 99),
            item.category,
        ),
    )[0]


def build_tfvars_patch(tfvars_key: str, current_value: str, proposed_value: str) -> str:
    return "\n".join(
        [
            f"# Suggested terraform.tfvars update for {tfvars_key}",
            f'- {tfvars_key} = "{current_value}"',
            f'+ {tfvars_key} = "{proposed_value}"',
        ]
    )
