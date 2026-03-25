import json
from pathlib import Path

from finops_agent.terraform_actions import (
    generate_terraform_actions,
    load_metrics,
    load_recommendations,
    load_tfvars,
)


BASE_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = BASE_DIR / "outputs"
TERRAFORM_DIR = BASE_DIR / "terraform"


def main():
    metrics_path = OUTPUTS_DIR / "metrics.json"
    recommendations_path = OUTPUTS_DIR / "recommendations.json"
    tfvars_path = TERRAFORM_DIR / "terraform.tfvars"
    output_path = OUTPUTS_DIR / "terraform_actions.json"
    patch_output_path = OUTPUTS_DIR / "terraform_actions.patch"

    if not metrics_path.is_file() or not recommendations_path.is_file():
        raise FileNotFoundError(
            "metrics.json and recommendations.json must exist in outputs/ before generating Terraform actions."
        )

    metrics = load_metrics(metrics_path)
    recommendations = load_recommendations(recommendations_path)
    tfvars = load_tfvars(tfvars_path)
    action_payload = generate_terraform_actions(metrics, recommendations, tfvars)

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(action_payload, indent=2), encoding="utf-8")
    patch_output_path.write_text(
        action_payload.get("tfvars_patch_preview", "") + ("\n" if action_payload.get("tfvars_patch_preview") else ""),
        encoding="utf-8",
    )

    summary = action_payload["summary"]
    print(
        "Terraform actions written:"
        f" {output_path.name}, {patch_output_path.name} | candidates={summary['candidate_instances']}"
        f" | proposed={summary['proposed_actions']}"
        f" | skipped={summary['skipped_instances']}"
    )


if __name__ == "__main__":
    main()
