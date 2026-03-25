# FinOps AI Agent

GCP infrastructure analytics pipeline for telemetry collection, rule-based analysis, historical enrichment, BigQuery storage, AI-assisted reporting, and data quality checks.

## Overview

This project analyzes Google Compute Engine VM telemetry and combines:

- SRE-oriented infrastructure visibility
- FinOps-oriented optimization findings
- data-engineering style collection, storage, and validation

Each run can:

- discover Compute Engine instances across zones
- collect CPU, memory, disk, network, uptime, lifecycle, and estimated cost signals
- generate deterministic recommendations from snapshot and trend signals
- enrich current records with 7-day history from BigQuery
- provision and re-provision the project VM with Terraform
- translate selected findings into Terraform machine-type change proposals
- write local JSON and Markdown artifacts
- append telemetry and recommendations to BigQuery
- generate a report with Gemini or deterministic fallback
- run basic data quality checks

## Features

### Snapshot Metrics

- instance metadata: name, zone, machine type, status, labels, creation time
- utilization: average CPU and memory
- throughput: disk read/write bytes and network in/out bytes
- lifecycle: uptime and instance age
- reference cost: estimated hourly and monthly VM cost

### Historical Enrichment

When BigQuery history is available, the collector adds:

- `seven_day_avg_cpu`
- `seven_day_low_utilization_days`
- `idle_but_expensive_flag`

### Recommendation Domains and Categories

Implemented recommendation domains:

- `finops`
- `sre`
- `governance`

Implemented categories by domain:

- `finops`
  - `idle-instance`
  - `rightsizing`
  - `lifecycle`
  - `stale-capacity`
  - `cost-awareness`
  - `persistent-low-utilization`
  - `idle-but-expensive`
- `sre`
  - `review-before-rightsizing`
  - `memory-bound`
  - `high-cpu-sustained`
  - `high-memory-pressure`
  - `missing-observability`
  - `high-network-throughput`
  - `high-disk-activity`
  - `long-lived-running-instance`
- `governance`
  - `governance`

### Agent Decision Fields

Each recommendation now includes decision-oriented fields:

- `action_priority`
  - priority label such as `p1`, `p2`, `p3`, `p4`
- `needs_human_review`
  - whether the finding should be explicitly reviewed by a person before action
- `recommended_owner`
  - suggested owner derived from labels and rule domain

Priority meaning used in findings and emails:

- `p1`
  - highest priority; immediate review recommended
- `p2`
  - elevated priority; important SRE-style review item
- `p3`
  - normal follow-up priority; optimization or governance work item
- `p4`
  - low priority; informational or non-urgent follow-up

## Architecture

1. `collector.py` loads configuration and queries GCP APIs plus Cloud Monitoring.
2. Telemetry is normalized into structured VM records.
3. Deterministic rules generate recommendations from snapshot and trend signals.
4. Outputs are written to `outputs/`.
5. If `BIGQUERY_DATASET` is configured, rows are appended to BigQuery tables.
6. `summarizer.py` generates JSON and Markdown reports.
7. `quality_check.py` validates run completeness and basic trustworthiness.
8. `terraform_actions.py` turns eligible findings into Terraform patch proposals.

## Project Structure

```text
FinOps-AI-Agent/
├── collector.py
├── summarizer.py
├── emailer.py
├── quality_check.py
├── terraform_actions.py
├── requirements.txt
├── terraform/
│   ├── main.tf
│   ├── outputs.tf
│   ├── terraform.tfvars.example
│   ├── variables.tf
│   └── versions.tf
├── tests/
│   ├── test_emailer.py
│   ├── test_quality_check.py
│   ├── test_rules.py
│   ├── test_summarizer.py
│   ├── test_terraform_actions.py
│   └── test_trends.py
├── finops_agent/
│   ├── __init__.py
│   ├── bigquery_writer.py
│   ├── metrics.py
│   ├── pricing.py
│   ├── rules.py
│   ├── schema.py
│   ├── terraform_actions.py
│   └── trends.py
└── outputs/
```

## Requirements

- Python 3.11+
- Terraform 1.5+
- a GCP project
- IAM access for:
  - `roles/compute.viewer`
  - `roles/monitoring.viewer`
- BigQuery access if warehouse export is enabled
- a local service account key or valid ADC configuration

## Installation

```bash
git clone https://github.com/KAILAI-Y/FinOps-AI-Agent.git
cd FinOps-AI-Agent
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

If you want to provision the demo environment with Terraform, also install Terraform locally.

## Configuration

Create a `.env` file in the project root.

### Minimum required `.env`

These values are required for GCP collection:

```ini
GCP_PROJECT_ID=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/gcp-key.json
```

### Optional `.env`

These values enable BigQuery export and Gemini generation:

```ini
BIGQUERY_DATASET=finops_agent
GEMINI_API_KEY=your-api-key
GEMINI_MODEL=gemini-2.5-flash
```

### Optional SMTP `.env`

These values enable actual email delivery from `emailer.py`:

```ini
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_gmail@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_USE_TLS=true
EMAIL_FROM=your_gmail@gmail.com
EMAIL_TO=recipient@example.com
```

Notes:

- `.env` is expected by `collector.py`, `summarizer.py`, and `emailer.py`
- `GOOGLE_APPLICATION_CREDENTIALS` can be omitted if `gcp-key.json` is placed in the repository root
- `BIGQUERY_DATASET` is optional
- `GEMINI_API_KEY` is optional; without it, report generation uses deterministic fallback
- if SMTP variables are missing, `emailer.py` still writes preview files but does not send mail
- for Gmail SMTP, use an App Password instead of your normal account password
- Terraform does not read `.env` automatically; set `credentials_file` in `terraform.tfvars` or use Application Default Credentials

## Quick Start

For a first successful run:

1. create a `.env` file with at least `GCP_PROJECT_ID` and `GOOGLE_APPLICATION_CREDENTIALS`
2. run the collector to generate telemetry and recommendations
3. generate the report, quality summary, and optional email preview

```bash
./venv/bin/python collector.py
./venv/bin/python summarizer.py
./venv/bin/python quality_check.py
./venv/bin/python emailer.py
./venv/bin/python terraform_actions.py
```

If SMTP is not configured, the last step still generates:

- `outputs/email_preview.json`
- `outputs/email_preview.txt`
- `outputs/email_preview.html`

## Usage

Run the full pipeline in this order:

```bash
./venv/bin/python collector.py
./venv/bin/python summarizer.py
./venv/bin/python quality_check.py
./venv/bin/python emailer.py
./venv/bin/python terraform_actions.py
```

### `collector.py`

- loads environment variables
- authenticates to GCP
- discovers VM instances
- collects telemetry
- enriches records with 7-day BigQuery history when available
- prints a terminal summary table and trend summary
- writes local JSON artifacts
- appends rows to BigQuery when enabled

### `summarizer.py`

- loads `metrics.json` and `recommendations.json`
- builds report context
- calls Gemini when available
- falls back to deterministic summary when needed
- writes JSON and Markdown report outputs

The report explicitly separates:

- snapshot findings
- trend findings

It also carries decision metadata for each finding, including:

- domain
- action priority
- recommended owner
- human review requirement

### `quality_check.py`

This step checks for:

- empty metrics output
- missing CPU data on running instances
- missing ownership labels
- stopped instances with recent activity in the lookback window
- null-heavy metric fields

### `emailer.py`

- loads `finops_report.json`, `quality_report.json`, `trend_analysis.json`, and `recommendations.json`
- builds an email context from findings, quality results, and trend summary
- uses Gemini to generate email subject, plain text, and HTML when available
- falls back to a deterministic email template when Gemini is unavailable
- writes local preview files
- sends the email through SMTP when SMTP configuration is present

### `terraform_actions.py`

- loads `metrics.json`, `recommendations.json`, and `terraform/terraform.tfvars`
- identifies right-sizing findings that can translate into Terraform changes
- skips proposals when conflicting SRE findings make downsizing unsafe
- generates a proposal payload instead of editing Terraform automatically
- writes `outputs/terraform_actions.json`

## Terraform

The `terraform/` directory provisions a minimal demo environment for this project:

- a single project VM in Compute Engine
- a Debian-based boot disk for that VM
- labels that align the VM with FinOps and Terraform governance checks

It is intended for project and demo infrastructure. Existing production-style VMs are better handled by the analytics pipeline plus Terraform action proposals, rather than direct Terraform takeover.

### Terraform setup

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply
```

### Terraform variables

At minimum, set this in `terraform.tfvars`:

```hcl
project_id = "your-project-id"
credentials_file = "/absolute/path/to/gcp-key.json"
```

You can also override:

- `region`
- `zone`
- `instance_name`
- `machine_type`
- `owner_label`
- `team_label`
- `environment_label`
- `cost_center_label`
- `existing_network_name`
- `existing_subnetwork_name`

If you prefer ADC instead of a key file, leave `credentials_file` empty and run:

```bash
gcloud auth application-default login
```

### Terraform outputs

After `terraform apply`, Terraform returns:

- demo VM name
- demo VM external IP

### Terraform action proposals

After `collector.py` generates recommendations, you can create Terraform change proposals with:

```bash
./venv/bin/python terraform_actions.py
```

The current implementation focuses on right-sizing proposals:

- it looks for categories such as `rightsizing`, `persistent-low-utilization`, `idle-but-expensive`, and `idle-instance`
- it blocks machine-type changes when SRE findings such as `memory-bound`, `missing-observability`, or `high-cpu-sustained` are present
- it proposes a `machine_type` update in `terraform.tfvars` instead of applying changes directly
- it also writes a patch-style preview for review before any Terraform apply step

## Outputs

Each run produces these local artifacts:

- `outputs/metrics.json`
  Latest structured VM telemetry, including 7-day trend fields when available
- `outputs/raw_metrics.json`
  Compatibility copy of the same telemetry payload
- `outputs/trend_analysis.json`
  Structured 7-day trend summary and per-instance trend view
- `outputs/recommendations.json`
  Deterministic findings generated by the rule engine, including domain, action priority, human review flag, and recommended owner
- `outputs/finops_report.json`
  Structured report output
- `outputs/finops_report.md`
  Markdown report with summary, actions, snapshot findings, and trend findings
- `outputs/quality_report.json`
  Structured data quality results
- `outputs/quality_report.md`
  Markdown data quality summary
- `outputs/email_preview.json`
  Structured email preview payload
- `outputs/email_preview.txt`
  Plain text email preview
- `outputs/email_preview.html`
  HTML email preview
- `outputs/terraform_actions.json`
  Terraform action proposal payload for right-sizing candidates managed by Terraform
- `outputs/terraform_actions.patch`
  Patch-style preview of the suggested `terraform.tfvars` machine type change

`collector.py` also prints a terminal snapshot table with:

- `Instance Name`
- `Status`
- `CPU %`
- `Memory %`
- `Est. Monthly Cost`
- `Triggered Rules`

When historical data is available, it also prints a `Trend Summary` section with:

- 7-day average CPU
- 7-day low-utilization day count
- idle-but-expensive flag

## BigQuery Tables

If `BIGQUERY_DATASET` is configured, the collector appends rows to:

- `your-project.<dataset>.raw_metrics`
- `your-project.<dataset>.recommendations`

The `raw_metrics` table stores current telemetry plus historical enrichment fields:

- `seven_day_avg_cpu`
- `seven_day_low_utilization_days`
- `idle_but_expensive_flag`

The `recommendations` table stores decision-oriented fields such as:

- `domain`
- `action_priority`
- `needs_human_review`
- `recommended_owner`

## Testing

The repository includes offline unit tests for:

- recommendation logic
- quality checks
- report fallback logic
- historical trend field application
- Terraform action proposal generation

Run all tests with:

```bash
./venv/bin/python -m unittest discover -s tests -v
```

Current expected result:

- `Ran 18 tests`
- `OK`

## Example Questions This Project Can Answer

- Which instances stayed under 10% CPU across recent days?
- Which VMs are underutilized but still relatively expensive?
- Which resources have governance gaps such as missing ownership labels?
- Which stopped instances may still need lifecycle cleanup review?
- Which findings come from the latest snapshot versus historical trend signals?

## Tech Stack

- Python 3.11
- Google Compute Engine API
- Google Cloud Monitoring API
- Google BigQuery
- Google Gemini API
