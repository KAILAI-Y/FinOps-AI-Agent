import unittest

from finops_agent.schema import VMMetric
from finops_agent.trends import apply_historical_trends, build_trend_analysis


class TrendsTestCase(unittest.TestCase):
    def test_apply_historical_trends_updates_metric_fields(self):
        metrics = [
            VMMetric(
                instance_name="trend-vm",
                machine_type="e2-standard-2",
                zone="us-central1-a",
                instance_id="vm-1",
                status="RUNNING",
            )
        ]
        trends = {
            "vm-1": {
                "seven_day_avg_cpu": 4.25,
                "seven_day_low_utilization_days": 5,
                "idle_but_expensive_flag": True,
            }
        }

        updated_metrics = apply_historical_trends(metrics, trends)
        metric = updated_metrics[0]

        self.assertEqual(metric.seven_day_avg_cpu, 4.25)
        self.assertEqual(metric.seven_day_low_utilization_days, 5)
        self.assertTrue(metric.idle_but_expensive_flag)

    def test_build_trend_analysis_summarizes_and_sorts_instances(self):
        metrics = [
            VMMetric(
                instance_name="vm-a",
                machine_type="e2-standard-2",
                zone="us-central1-a",
                instance_id="vm-a",
                status="RUNNING",
                seven_day_avg_cpu=4.25,
                seven_day_low_utilization_days=5,
                idle_but_expensive_flag=True,
                estimated_monthly_cost=120.0,
            ),
            VMMetric(
                instance_name="vm-b",
                machine_type="e2-standard-2",
                zone="us-central1-a",
                instance_id="vm-b",
                status="RUNNING",
                seven_day_avg_cpu=8.0,
                seven_day_low_utilization_days=3,
                idle_but_expensive_flag=False,
                estimated_monthly_cost=20.0,
            ),
            VMMetric(
                instance_name="vm-c",
                machine_type="e2-standard-2",
                zone="us-central1-a",
                instance_id="vm-c",
                status="RUNNING",
            ),
        ]

        payload = build_trend_analysis(metrics)

        self.assertEqual(payload["summary"]["trend_ready_instances"], 2)
        self.assertEqual(payload["summary"]["persistent_low_utilization_instances"], 2)
        self.assertEqual(payload["summary"]["idle_but_expensive_instances"], 1)
        self.assertEqual(payload["instances"][0]["instance_name"], "vm-a")
        self.assertEqual(payload["instances"][1]["instance_name"], "vm-b")


if __name__ == "__main__":
    unittest.main()
