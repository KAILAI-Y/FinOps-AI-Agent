# FinOps-AI-Agent 🚀

**A cloud cost optimization data pipeline that collects GCP infrastructure telemetry, generates FinOps recommendations, stores results in BigQuery, and produces actionable Gemini reports.**

## Overview

Keeping cloud estates lean in 2026 is as critical as keeping them reliable. FinOps-AI-Agent bridges observability with FinOps discipline: it discovers Google Cloud resources, profiles utilization, scores optimization opportunities with deterministic rules, lands results in BigQuery, and generates actionable reports for cost review.

## At a Glance

- Collects GCP VM telemetry across CPU, memory, disk, network, uptime, and estimated cost
- Converts infrastructure signals into deterministic FinOps findings such as governance gaps, lifecycle cleanup, and rightsizing review
- Stores run outputs in BigQuery for historical analysis and SQL-based querying
- Generates Gemini reports with concrete checks, decision rules, and next actions
- Validates run quality with a lightweight data quality report

## Why This Project Matters

This project is designed to demonstrate data engineering and FinOps analytics skills in one workflow:

- Ingests real cloud telemetry from GCP APIs instead of relying on mock data
- Normalizes infrastructure metrics into structured artifacts and warehouse tables
- Applies deterministic business rules to convert monitoring data into optimization findings
- Uses Gemini to turn technical signals into actionable operator guidance
- Includes data quality checks so each run can be validated before downstream use

## Key Capabilities

- Multi-zone GCE discovery with CPU, memory, disk, network, uptime, and estimated cost telemetry
- Rule-based FinOps recommendation engine for governance, lifecycle, and rightsizing review
- Optional BigQuery export for historical storage and SQL-based analysis
- Gemini-generated cost optimization reports with concrete verification steps and decision rules
- Local quality reports for null checks, ownership-label coverage, and suspicious state/activity patterns

## End-to-End Flow

1. `collector.py` queries GCP APIs and Cloud Monitoring for VM-level telemetry.
2. The rule engine converts raw signals into FinOps recommendations.
3. Results are written to `outputs/` and optionally appended to BigQuery tables.
4. `summarizer.py` turns the latest run into an actionable Gemini report.
5. `quality_check.py` validates whether the run is complete and trustworthy.

## Architecture Snapshot

| Phase                                 | Status      | Highlights                                                                                  |
| ------------------------------------- | ----------- | ------------------------------------------------------------------------------------------- |
| Phase 1 – Metrics + Rule Engine       | ✅ Complete    | Multi-zone GCE discovery, utilization + cost telemetry, rule-based recommendations, BigQuery export |
| Phase 2 – LLM Insights                | 🛠 In Progress | Gemini-powered FinOps reports with actionable checks, decision rules, and fallback summaries |
| Phase 3 – Alerting & Collaboration    | 🛠 Planned  | Slack/Email alerts with remediation playbooks                                               |
| Phase 4 – Self-healing GitOps Loop    | 🛠 Planned  | Auto-create Terraform PRs to resize or schedule instances                                   |

## Tech Stack

- **Cloud:** Google Cloud Platform (Compute Engine, Cloud Monitoring)
- **Language:** Python 3.11
- **Auth:** IAM Service Accounts (least-privilege)
- **AI Tooling:** Google Gemini API (implemented), LangChain (planned)

## Project Structure

```text
FinOps-AI-Agent/
├── collector.py              # Metrics collection entrypoint
├── summarizer.py             # Gemini / fallback report entrypoint
├── quality_check.py          # Data quality validation entrypoint
├── finops_agent/
│   ├── bigquery_writer.py    # BigQuery export helpers
│   ├── metrics.py            # Cloud Monitoring access helpers
│   ├── pricing.py            # Lightweight cost estimation
│   ├── rules.py              # Deterministic recommendation engine
│   └── schema.py             # Shared data models
├── outputs/                  # Local runtime artifacts (generated)
├── README.md
└── requirements.txt
```

## Getting Started

### Prerequisites

- Python 3.11+
- A GCP project where you can grant `roles/compute.viewer` and `roles/monitoring.viewer` to the collector service account
- `gcp-key.json` service-account key stored at the repository root (ignored by git)

### Installation

```bash
git clone https://github.com/KAILAI-Y/FinOps-AI-Agent.git
cd FinOps-AI-Agent
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Quick Start

```bash
./venv/bin/python collector.py
./venv/bin/python summarizer.py
./venv/bin/python quality_check.py
```

After configuration and one full run, inspect:

- `outputs/metrics.json`
- `outputs/recommendations.json`
- `outputs/finops_report.md`
- `outputs/quality_report.md`

### Configuration

1. Place `gcp-key.json` in the project root.
2. Create a `.env` file (auto-loaded by `collector.py` and `summarizer.py`):
   ```ini
   GCP_PROJECT_ID=your-project-id
   GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/gcp-key.json  # optional; auto-set if omitted
   BIGQUERY_DATASET=finops_agent  # optional; enables warehouse export
   ```

### Run the Metrics Collector

```bash
./venv/bin/python collector.py
```

The script:

1. Loads variables from `.env`.
2. Ensures Google Application Default Credentials point to `gcp-key.json` (or respects your manual setting).
3. Discovers all Compute Engine instances across zones.
4. Fetches the past hour of CPU utilization via Cloud Monitoring.
5. Collects additional telemetry such as memory use, disk I/O, network throughput, instance age, uptime, and estimated cost.
6. Builds deterministic FinOps recommendations before any LLM layer is introduced.
7. Prints a styled terminal table and writes JSON outputs for downstream analysis.

### Generate an LLM Report

Set these optional variables if you want a Gemini-generated report:

```ini
GEMINI_API_KEY=your-api-key
GEMINI_MODEL=gemini-2.5-flash
```

Then run:

```bash
./venv/bin/python summarizer.py
```

If Gemini credentials are unavailable or the API call fails, the script falls back to a deterministic summary and still writes report files.

### Run Data Quality Checks

```bash
./venv/bin/python quality_check.py
```

This writes:

- `outputs/quality_report.json`
- `outputs/quality_report.md`

The report flags empty outputs, RUNNING instances with missing CPU data, missing ownership labels, stopped instances with recent activity in the lookback window, and null-heavy metric fields.

## Output

- **Terminal:** colorized table summarizing instance name, machine type, zone, and CPU%.
- **Files:**
  - `outputs/metrics.json` / `outputs/raw_metrics.json` – structured telemetry for downstream analysis.
  - `outputs/recommendations.json` – rule-based optimization findings to feed later LLM summarization.
  - `outputs/finops_report.json` / `outputs/finops_report.md` – final summarized report from Gemini or fallback logic.
  - `outputs/quality_report.json` / `outputs/quality_report.md` – basic data quality validation for each run.
- **Warehouse (optional):**
  - `BIGQUERY_DATASET` is set, the collector also writes to BigQuery tables:
    - `your-project.finops_agent.raw_metrics`
    - `your-project.finops_agent.recommendations`

Current telemetry includes:

- Instance metadata: machine type, zone, status, labels, creation timestamp
- Utilization: average CPU and memory over the last hour
- Throughput: disk read/write bytes and network in/out bytes over the last hour
- Lifecycle: instance age in hours and latest reported uptime total
- Cost estimate: approximate hourly and monthly cost from a local machine-type pricing table

## What This Repository Demonstrates

- Data ingestion from real cloud APIs
- Metric normalization and schema design
- Rule-based analytics over infrastructure telemetry
- Warehouse export and SQL-friendly outputs
- AI-assisted reporting with explicit operational guidance
- Basic data quality controls for downstream trust

## Rule Engine

The current recommendation layer is deterministic. It converts raw telemetry into FinOps findings before any LLM summarization is added.

| Rule | Trigger | Meaning | Typical action |
| ---- | ------- | ------- | -------------- |
| `idle-instance` | Very low CPU, low memory, and low disk/network activity | The VM looks mostly idle | Validate ownership, then stop on a schedule or downsize |
| `rightsizing` | Low CPU and low memory utilization | The VM may be larger than needed | Review historical peaks and test a smaller machine type |
| `review-before-rightsizing` | Low CPU but noticeable disk or network activity | The workload may be I/O-bound, not oversized | Inspect throughput patterns before changing instance size |
| `memory-bound` | Low CPU but high memory utilization | The workload may be constrained by memory | Avoid shrinking memory footprint without deeper review |
| `governance` | Missing ownership or chargeback labels | FinOps accountability is incomplete | Add `env`, `owner`, `team`, and `cost-center` labels |
| `lifecycle` | Instance is not `RUNNING` | Stopped resources may still have attached billable assets | Review disks, IPs, and other leftover resource costs |
| `stale-capacity` | Long-lived instance with low utilization | Legacy always-on capacity may no longer be justified | Review whether the workload still needs continuous runtime |
| `cost-awareness` | Estimated monthly run cost crosses a review threshold | Higher-cost instances deserve earlier optimization review | Prioritize this VM when opportunities are found |

## BigQuery Export

If `BIGQUERY_DATASET` is configured, the collector will create the dataset if needed and write each run to two BigQuery tables:

- `raw_metrics`: one row per VM per collector run
- `recommendations`: one row per recommendation, with a `run_timestamp`

This makes the project easier to position as a data engineering workflow, because the collected telemetry can be queried with SQL instead of only being stored as local JSON.

Each collector run appends new rows to BigQuery. If you run the script every day or on a schedule, the warehouse tables naturally accumulate historical samples over time.

## Example Queries

`latest_vm_metrics_snapshot`

```sql
SELECT
  timestamp,
  instance_name,
  machine_type,
  zone,
  cpu_utilization_avg,
  memory_utilization_avg,
  estimated_monthly_cost
FROM `gen-lang-client-0054994791.finops_agent.raw_metrics`
ORDER BY timestamp DESC
LIMIT 20;
```

`seven_day_low_utilization_instances`

```sql
SELECT
  instance_name,
  AVG(cpu_utilization_avg) AS avg_cpu,
  AVG(memory_utilization_avg) AS avg_memory,
  AVG(estimated_monthly_cost) AS avg_monthly_cost,
  COUNT(*) AS samples
FROM `gen-lang-client-0054994791.finops_agent.raw_metrics`
WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY instance_name
ORDER BY avg_cpu ASC;
```

`latest_finops_recommendations`

```sql
SELECT
  run_timestamp,
  instance_name,
  category,
  severity,
  summary
FROM `gen-lang-client-0054994791.finops_agent.recommendations`
ORDER BY run_timestamp DESC
LIMIT 50;
```

`thirty_day_recommendation_summary`

```sql
SELECT
  category,
  severity,
  COUNT(*) AS recommendation_count
FROM `gen-lang-client-0054994791.finops_agent.recommendations`
WHERE run_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY category, severity
ORDER BY recommendation_count DESC;
```

## Sample Report Output

Example of the generated FinOps report after metrics collection and Gemini summarization:

```md
# FinOps Report

## Terminated GCP Instance Flagged for Leftover Resource Review and Labeling Gaps

The instance is currently terminated, so it is not consuming compute resources. However, the report highlights two follow-up checks: possible leftover billable resources such as disks or reserved IPs, and missing ownership labels that weaken cost governance.

### How To Check
- Inspect the VM in Compute Engine and review attached disks.
- Check Persistent Disks for leftover unattached volumes.
- Review reserved IP addresses in VPC Network.
- Verify whether `env`, `owner`, `team`, and `cost-center` labels are missing.

### Recommended Action
Delete or release unused leftover resources after verification, then apply the required ownership labels.
```

## Current Scope

Included now:

- GCP Compute Engine VM telemetry collection
- Rule-based FinOps recommendations
- BigQuery export
- Gemini report generation
- Local data quality reporting

Planned next:

- Alerting and collaboration workflows
- Additional cost sources beyond VM reference pricing
- GitOps or remediation automation

## Roadmap

- [x] Milestone 1: Robust GCP metrics collector.
- [x] Milestone 2: Initial rule-based recommendation layer.
- [~] Milestone 3: Gemini-powered report generation and actionable summaries.
- [ ] Milestone 4: Automated alerting to Slack/Email.
- [ ] Milestone 5: GitOps-based self-healing (Terraform PRs for resizing/shutdown).

## Contributing

Issues and PRs are welcome—please document environment assumptions and include reproduction steps for any bug reports.
