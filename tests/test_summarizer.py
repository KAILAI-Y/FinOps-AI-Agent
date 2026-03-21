import unittest

from summarizer import build_fallback_summary, build_report_context


class SummarizerFallbackTestCase(unittest.TestCase):
    def test_fallback_summary_prioritizes_highest_severity_recommendation(self):
        metrics = [
            {
                "instance_name": "idle-vm",
                "status": "RUNNING",
                "estimated_monthly_cost": 120.0,
                "seven_day_avg_cpu": 4.5,
                "seven_day_low_utilization_days": 5,
                "idle_but_expensive_flag": True,
            },
            {
                "instance_name": "stopped-vm",
                "status": "TERMINATED",
                "estimated_monthly_cost": 0.0,
                "seven_day_avg_cpu": None,
                "seven_day_low_utilization_days": 0,
                "idle_but_expensive_flag": False,
            },
        ]
        recommendations = [
            {
                "instance_name": "stopped-vm",
                "domain": "finops",
                "category": "lifecycle",
                "severity": "low",
                "action_priority": "p4",
                "needs_human_review": True,
                "recommended_owner": "platform",
                "summary": "Stopped instance may still have attached assets.",
                "rationale": "Stopped resources may still have attached assets.",
                "suggested_action": "Review attached resources.",
            },
            {
                "instance_name": "idle-vm",
                "domain": "finops",
                "category": "idle-instance",
                "severity": "high",
                "action_priority": "p1",
                "needs_human_review": True,
                "recommended_owner": "finops-team",
                "summary": "Idle instance appears mostly unused.",
                "rationale": "Average CPU is persistently near zero with low activity.",
                "suggested_action": "Validate ownership and stop on a schedule.",
            },
            {
                "instance_name": "idle-vm",
                "domain": "finops",
                "category": "persistent-low-utilization",
                "severity": "medium",
                "action_priority": "p3",
                "needs_human_review": True,
                "recommended_owner": "finops-team",
                "summary": "Low utilization has persisted across multiple days.",
                "rationale": "Historical CPU stayed low across recent days.",
                "suggested_action": "Validate whether always-on runtime is still needed.",
            },
            {
                "instance_name": "idle-vm",
                "domain": "governance",
                "category": "governance",
                "severity": "medium",
                "action_priority": "p3",
                "needs_human_review": True,
                "recommended_owner": "platform-team",
                "summary": "Ownership labels are incomplete.",
                "rationale": "Ownership labels are incomplete.",
                "suggested_action": "Populate env, owner, team, and cost-center labels.",
            },
        ]

        context = build_report_context(metrics, recommendations)
        report = build_fallback_summary(context)

        self.assertEqual(report["mode"], "deterministic")
        self.assertEqual(report["primary_candidate"], "idle-vm")
        self.assertIn("idle-instance", report["headline"])
        self.assertIn("Validate ownership and stop on a schedule.", report["actions"])
        self.assertTrue(report["risks"])
        self.assertEqual(len(report["how_to_check"]), 3)
        self.assertIn("Historical trend coverage is available", report["summary"])
        self.assertIn("Snapshot findings: 3. Trend findings: 1.", report["summary"])
        self.assertIn("Domain breakdown: finops 3, governance 1.", report["summary"])
        self.assertEqual(len(report["snapshot_findings"]), 3)
        self.assertEqual(len(report["trend_findings"]), 1)
        self.assertEqual(report["trend_findings"][0]["category"], "persistent-low-utilization")
        self.assertEqual(report["trend_findings"][0]["domain"], "finops")
        self.assertEqual(report["trend_findings"][0]["action_priority"], "p3")
        self.assertTrue(report["trend_findings"][0]["needs_human_review"])

    def test_fallback_summary_handles_empty_recommendations(self):
        metrics = [
            {
                "instance_name": "quiet-vm",
                "status": "RUNNING",
                "estimated_monthly_cost": 10.0,
                "seven_day_avg_cpu": None,
                "seven_day_low_utilization_days": 0,
                "idle_but_expensive_flag": False,
            }
        ]
        recommendations = []

        context = build_report_context(metrics, recommendations)
        report = build_fallback_summary(context)

        self.assertEqual(report["primary_candidate"], "None")
        self.assertEqual(report["recommended_action"], "No action suggested.")
        self.assertEqual(report["why_it_matters"], "No optimization findings were generated.")
        self.assertEqual(report["snapshot_findings"], [])
        self.assertEqual(report["trend_findings"], [])


if __name__ == "__main__":
    unittest.main()
