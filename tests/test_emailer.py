import unittest

from emailer import build_email_context, build_fallback_email


class EmailerTestCase(unittest.TestCase):
    def test_build_email_context_and_fallback_email(self):
        report = {
            "headline": "Top finding: idle-vm requires idle-instance review.",
            "primary_candidate": "idle-vm",
            "recommended_action": "Validate ownership and stop on a schedule.",
            "snapshot_findings": [],
            "trend_findings": [],
        }
        quality_report = {"summary": {"pass": 3, "warn": 1, "fail": 0, "info": 1}}
        trend_analysis = {
            "summary": {
                "trend_ready_instances": 1,
                "persistent_low_utilization_instances": 1,
                "idle_but_expensive_instances": 0,
            }
        }
        recommendations = [
            {
                "instance_name": "idle-vm",
                "domain": "finops",
                "category": "idle-instance",
                "action_priority": "p1",
                "recommended_owner": "finops-team",
                "needs_human_review": True,
                "severity": "high",
                "summary": "Idle instance appears mostly unused.",
            },
            {
                "instance_name": "idle-vm",
                "domain": "finops",
                "category": "persistent-low-utilization",
                "action_priority": "p3",
                "recommended_owner": "finops-team",
                "needs_human_review": True,
                "severity": "medium",
                "summary": "Low utilization has persisted across multiple days.",
            },
        ]

        context = build_email_context(report, quality_report, trend_analysis, recommendations)
        payload = build_fallback_email(context)

        self.assertIn("idle-vm", payload["subject"])
        self.assertIn("Snapshot findings: 0", payload["plain_text"])
        self.assertIn("Trend findings: 0", payload["plain_text"])
        self.assertIn("Top findings:", payload["plain_text"])
        self.assertIn("finops-team", payload["plain_text"])
        self.assertIn("<html>", payload["html"])
        self.assertEqual(payload["mode"], "deterministic")


if __name__ == "__main__":
    unittest.main()
