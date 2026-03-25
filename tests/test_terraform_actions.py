import unittest

from finops_agent.schema import Recommendation, VMMetric
from finops_agent.terraform_actions import generate_terraform_actions, load_tfvars


class TerraformActionsTestCase(unittest.TestCase):
    def test_generates_rightsizing_action_for_terraform_managed_vm(self):
        metrics = [
            VMMetric(
                instance_name="finops-agent-demo-vm",
                machine_type="e2-medium",
                zone="us-central1-c",
                instance_id="123",
                status="RUNNING",
                labels={"managed_by": "terraform", "owner": "ops", "team": "platform"},
                cpu_utilization_avg=4.0,
                memory_utilization_avg=20.0,
                estimated_monthly_cost=24.38,
            )
        ]
        recommendations = [
            Recommendation(
                instance_name="finops-agent-demo-vm",
                domain="finops",
                category="rightsizing",
                severity="medium",
                action_priority="p3",
                needs_human_review=True,
                recommended_owner="ops",
                summary="Instance may be oversized for current workload.",
                rationale="Average CPU utilization is low.",
                suggested_action="Review a smaller machine type.",
                estimated_savings_hint="Moderate savings likely.",
            )
        ]
        tfvars = {"instance_name": "finops-agent-demo-vm", "machine_type": "e2-medium"}

        payload = generate_terraform_actions(metrics, recommendations, tfvars)

        self.assertEqual(payload["summary"]["proposed_actions"], 1)
        action = payload["actions"][0]
        self.assertEqual(action["tfvars_key"], "machine_type")
        self.assertEqual(action["current_value"], "e2-medium")
        self.assertEqual(action["proposed_value"], "e2-small")
        self.assertEqual(action["resource_address"], "google_compute_instance.demo_vm")
        self.assertIn('- machine_type = "e2-medium"', action["tfvars_patch"])
        self.assertIn('+ machine_type = "e2-small"', action["tfvars_patch"])
        self.assertIn('machine_type = "e2-small"', payload["tfvars_patch_preview"])

    def test_skips_when_conflicting_sre_finding_exists(self):
        metrics = [
            VMMetric(
                instance_name="finops-agent-demo-vm",
                machine_type="e2-standard-4",
                zone="us-central1-c",
                instance_id="456",
                status="RUNNING",
                labels={"managed_by": "terraform", "owner": "ops", "team": "platform"},
                cpu_utilization_avg=5.0,
                memory_utilization_avg=80.0,
            )
        ]
        recommendations = [
            Recommendation(
                instance_name="finops-agent-demo-vm",
                domain="finops",
                category="rightsizing",
                severity="medium",
                action_priority="p3",
                needs_human_review=True,
                recommended_owner="ops",
                summary="Instance may be oversized for current workload.",
                rationale="Average CPU utilization is low.",
                suggested_action="Review a smaller machine type.",
                estimated_savings_hint="Moderate savings likely.",
            ),
            Recommendation(
                instance_name="finops-agent-demo-vm",
                domain="sre",
                category="memory-bound",
                severity="medium",
                action_priority="p2",
                needs_human_review=True,
                recommended_owner="platform",
                summary="CPU is low but memory usage is relatively high.",
                rationale="Memory usage is high.",
                suggested_action="Avoid downsizing.",
                estimated_savings_hint="Avoid cost-saving actions that create contention.",
            ),
        ]
        tfvars = {"instance_name": "finops-agent-demo-vm", "machine_type": "e2-standard-4"}

        payload = generate_terraform_actions(metrics, recommendations, tfvars)

        self.assertEqual(payload["summary"]["proposed_actions"], 0)
        self.assertEqual(payload["summary"]["skipped_instances"], 1)
        self.assertIn("memory-bound", payload["skipped"][0]["reason"])
        self.assertEqual(payload["tfvars_patch_preview"], "")

    def test_load_tfvars_parses_simple_assignments(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as temp_dir:
            tfvars_path = Path(temp_dir) / "terraform.tfvars"
            tfvars_path.write_text(
                'project_id = "demo-project"\ninstance_name = "finops-agent-demo-vm"\n',
                encoding="utf-8",
            )

            values = load_tfvars(tfvars_path)

        self.assertEqual(values["project_id"], "demo-project")
        self.assertEqual(values["instance_name"], "finops-agent-demo-vm")


if __name__ == "__main__":
    unittest.main()
