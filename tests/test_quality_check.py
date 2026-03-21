import unittest

from quality_check import run_checks, summarize_checks


class QualityCheckTestCase(unittest.TestCase):
    def test_run_checks_emits_expected_warn_and_info_states(self):
        metrics = [
            {
                "instance_name": "terminated-vm",
                "status": "TERMINATED",
                "labels": {"env": "prod"},
                "cpu_utilization_avg": None,
                "memory_utilization_avg": 40.0,
                "disk_read_bytes_1h": 128.0,
                "disk_write_bytes_1h": 0.0,
                "network_in_bytes_1h": 0.0,
                "network_out_bytes_1h": 0.0,
                "uptime_total_seconds": 3600.0,
            }
        ]
        recommendations = [{"instance_name": "terminated-vm", "category": "lifecycle"}]

        checks = run_checks(metrics, recommendations)
        by_name = {check["name"]: check for check in checks}

        self.assertEqual(by_name["metrics_file_not_empty"]["status"], "pass")
        self.assertEqual(by_name["recommendations_file_present"]["status"], "pass")
        self.assertEqual(by_name["running_instances_have_cpu"]["status"], "info")
        self.assertEqual(by_name["ownership_labels_present"]["status"], "warn")
        self.assertEqual(by_name["stopped_instances_with_recent_activity"]["status"], "warn")
        self.assertEqual(by_name["null_heavy_fields"]["status"], "warn")

    def test_summarize_checks_counts_statuses(self):
        summary = summarize_checks(
            [
                {"status": "pass"},
                {"status": "warn"},
                {"status": "warn"},
                {"status": "info"},
                {"status": "fail"},
            ]
        )

        self.assertEqual(summary, {"pass": 1, "warn": 2, "fail": 1, "info": 1})


if __name__ == "__main__":
    unittest.main()
