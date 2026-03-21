import unittest

from finops_agent.rules import build_recommendations
from finops_agent.schema import VMMetric


class RulesTestCase(unittest.TestCase):
    def test_idle_instance_and_governance_are_flagged(self):
        metric = VMMetric(
            instance_name="idle-vm",
            machine_type="e2-standard-4",
            zone="us-central1-a",
            instance_id="123",
            status="RUNNING",
            labels={"env": "dev"},
            cpu_utilization_avg=1.5,
            memory_utilization_avg=20.0,
            disk_read_bytes_1h=0.0,
            disk_write_bytes_1h=0.0,
            network_in_bytes_1h=0.0,
            network_out_bytes_1h=0.0,
            estimated_monthly_cost=97.82,
        )

        recommendations = build_recommendations([metric])
        categories = {recommendation.category for recommendation in recommendations}
        domains_by_category = {recommendation.category: recommendation.domain for recommendation in recommendations}

        self.assertIn("idle-instance", categories)
        self.assertIn("governance", categories)
        self.assertIn("cost-awareness", categories)
        self.assertEqual(domains_by_category["idle-instance"], "finops")
        self.assertEqual(domains_by_category["governance"], "governance")
        self.assertEqual(domains_by_category["cost-awareness"], "finops")
        idle_finding = next(recommendation for recommendation in recommendations if recommendation.category == "idle-instance")
        self.assertEqual(idle_finding.action_priority, "p1")
        self.assertTrue(idle_finding.needs_human_review)
        self.assertEqual(idle_finding.recommended_owner, "finops-team")

    def test_memory_bound_prevents_rightsizing(self):
        metric = VMMetric(
            instance_name="memory-vm",
            machine_type="e2-standard-2",
            zone="us-central1-a",
            instance_id="456",
            status="RUNNING",
            labels={"env": "prod", "owner": "ops", "team": "platform", "cost-center": "cc1"},
            cpu_utilization_avg=5.0,
            memory_utilization_avg=85.0,
            disk_read_bytes_1h=0.0,
            disk_write_bytes_1h=0.0,
            network_in_bytes_1h=0.0,
            network_out_bytes_1h=0.0,
        )

        recommendations = build_recommendations([metric])
        categories = {recommendation.category for recommendation in recommendations}
        domains_by_category = {recommendation.category: recommendation.domain for recommendation in recommendations}

        self.assertIn("memory-bound", categories)
        self.assertNotIn("rightsizing", categories)
        self.assertEqual(domains_by_category["memory-bound"], "sre")
        memory_finding = next(recommendation for recommendation in recommendations if recommendation.category == "memory-bound")
        self.assertEqual(memory_finding.action_priority, "p2")
        self.assertTrue(memory_finding.needs_human_review)
        self.assertEqual(memory_finding.recommended_owner, "platform")

    def test_non_running_instance_gets_lifecycle_flag(self):
        metric = VMMetric(
            instance_name="stopped-vm",
            machine_type="e2-small",
            zone="us-central1-a",
            instance_id="789",
            status="TERMINATED",
            labels={"env": "prod", "owner": "ops", "team": "platform", "cost-center": "cc1"},
        )

        recommendations = build_recommendations([metric])
        categories = {recommendation.category for recommendation in recommendations}
        domains_by_category = {recommendation.category: recommendation.domain for recommendation in recommendations}

        self.assertIn("lifecycle", categories)
        self.assertEqual(domains_by_category["lifecycle"], "finops")
        lifecycle_finding = next(recommendation for recommendation in recommendations if recommendation.category == "lifecycle")
        self.assertEqual(lifecycle_finding.action_priority, "p4")
        self.assertTrue(lifecycle_finding.needs_human_review)

    def test_persistent_low_utilization_and_idle_but_expensive_are_flagged(self):
        metric = VMMetric(
            instance_name="trend-vm",
            machine_type="e2-standard-4",
            zone="us-central1-a",
            instance_id="101",
            status="RUNNING",
            labels={"env": "prod", "owner": "ops", "team": "platform", "cost-center": "cc1"},
            cpu_utilization_avg=4.0,
            memory_utilization_avg=22.0,
            disk_read_bytes_1h=0.0,
            disk_write_bytes_1h=0.0,
            network_in_bytes_1h=0.0,
            network_out_bytes_1h=0.0,
            estimated_monthly_cost=120.0,
            seven_day_avg_cpu=4.43,
            seven_day_low_utilization_days=3,
            idle_but_expensive_flag=True,
        )

        recommendations = build_recommendations([metric])
        categories = {recommendation.category for recommendation in recommendations}
        domains_by_category = {recommendation.category: recommendation.domain for recommendation in recommendations}

        self.assertIn("persistent-low-utilization", categories)
        self.assertIn("idle-but-expensive", categories)
        self.assertEqual(domains_by_category["persistent-low-utilization"], "finops")
        self.assertEqual(domains_by_category["idle-but-expensive"], "finops")
        expensive_finding = next(recommendation for recommendation in recommendations if recommendation.category == "idle-but-expensive")
        self.assertEqual(expensive_finding.action_priority, "p1")
        self.assertTrue(expensive_finding.needs_human_review)
        self.assertEqual(expensive_finding.recommended_owner, "ops")

    def test_high_cpu_and_high_memory_are_flagged_as_sre(self):
        metric = VMMetric(
            instance_name="hot-vm",
            machine_type="e2-standard-4",
            zone="us-central1-a",
            instance_id="202",
            status="RUNNING",
            labels={"env": "prod", "owner": "ops", "team": "platform", "cost-center": "cc1"},
            cpu_utilization_avg=92.0,
            memory_utilization_avg=91.0,
            disk_read_bytes_1h=0.0,
            disk_write_bytes_1h=0.0,
            network_in_bytes_1h=0.0,
            network_out_bytes_1h=0.0,
        )

        recommendations = build_recommendations([metric])
        categories = {recommendation.category for recommendation in recommendations}
        domains_by_category = {recommendation.category: recommendation.domain for recommendation in recommendations}

        self.assertIn("high-cpu-sustained", categories)
        self.assertIn("high-memory-pressure", categories)
        self.assertEqual(domains_by_category["high-cpu-sustained"], "sre")
        self.assertEqual(domains_by_category["high-memory-pressure"], "sre")
        cpu_finding = next(recommendation for recommendation in recommendations if recommendation.category == "high-cpu-sustained")
        self.assertEqual(cpu_finding.action_priority, "p1")
        self.assertTrue(cpu_finding.needs_human_review)
        self.assertEqual(cpu_finding.recommended_owner, "platform")

    def test_missing_observability_is_flagged_for_running_instance(self):
        metric = VMMetric(
            instance_name="blind-vm",
            machine_type="e2-standard-2",
            zone="us-central1-a",
            instance_id="303",
            status="RUNNING",
            labels={"env": "prod", "owner": "ops", "team": "platform", "cost-center": "cc1"},
            cpu_utilization_avg=None,
            memory_utilization_avg=None,
        )

        recommendations = build_recommendations([metric])
        categories = [recommendation.category for recommendation in recommendations]
        domains = [recommendation.domain for recommendation in recommendations if recommendation.category == "missing-observability"]

        self.assertEqual(categories.count("missing-observability"), 2)
        self.assertTrue(all(domain == "sre" for domain in domains))
        findings = [recommendation for recommendation in recommendations if recommendation.category == "missing-observability"]
        self.assertTrue(all(finding.needs_human_review for finding in findings))
        self.assertTrue(all(finding.recommended_owner == "platform" for finding in findings))

    def test_high_network_and_disk_activity_are_flagged_as_sre(self):
        metric = VMMetric(
            instance_name="busy-vm",
            machine_type="e2-standard-4",
            zone="us-central1-a",
            instance_id="404",
            status="RUNNING",
            labels={"env": "prod", "owner": "ops", "team": "platform", "cost-center": "cc1"},
            cpu_utilization_avg=35.0,
            memory_utilization_avg=50.0,
            disk_read_bytes_1h=2.5 * 1024 * 1024 * 1024,
            disk_write_bytes_1h=0.2 * 1024 * 1024 * 1024,
            network_in_bytes_1h=400 * 1024 * 1024,
            network_out_bytes_1h=200 * 1024 * 1024,
        )

        recommendations = build_recommendations([metric])
        categories = {recommendation.category for recommendation in recommendations}
        domains_by_category = {recommendation.category: recommendation.domain for recommendation in recommendations}

        self.assertIn("high-network-throughput", categories)
        self.assertIn("high-disk-activity", categories)
        self.assertEqual(domains_by_category["high-network-throughput"], "sre")
        self.assertEqual(domains_by_category["high-disk-activity"], "sre")

    def test_long_lived_running_instance_is_flagged_as_sre(self):
        metric = VMMetric(
            instance_name="aging-vm",
            machine_type="e2-standard-2",
            zone="us-central1-a",
            instance_id="505",
            status="RUNNING",
            labels={"env": "prod", "owner": "ops", "team": "platform", "cost-center": "cc1"},
            cpu_utilization_avg=18.0,
            memory_utilization_avg=45.0,
            instance_age_hours=(24 * 45),
        )

        recommendations = build_recommendations([metric])
        categories = {recommendation.category for recommendation in recommendations}
        finding = next(
            recommendation
            for recommendation in recommendations
            if recommendation.category == "long-lived-running-instance"
        )

        self.assertIn("long-lived-running-instance", categories)
        self.assertEqual(finding.domain, "sre")
        self.assertEqual(finding.action_priority, "p2")
        self.assertTrue(finding.needs_human_review)


if __name__ == "__main__":
    unittest.main()
