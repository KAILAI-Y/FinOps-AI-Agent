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

## Architecture

1. `collector.py` loads configuration and queries GCP APIs plus Cloud Monitoring.
2. Telemetry is normalized into structured VM records.
3. Deterministic rules generate recommendations from snapshot and trend signals.
4. Outputs are written to `outputs/`.
5. If `BIGQUERY_DATASET` is configured, rows are appended to BigQuery tables.
6. `summarizer.py` generates JSON and Markdown reports.
7. `quality_check.py` validates run completeness and basic trustworthiness.

## Project Structure

```text
FinOps-AI-Agent/
├── collector.py
├── summarizer.py
├── emailer.py
├── quality_check.py
├── requirements.txt
├── tests/
│   ├── test_emailer.py
│   ├── test_quality_check.py
│   ├── test_rules.py
│   ├── test_summarizer.py
│   └── test_trends.py
├── finops_agent/
│   ├── __init__.py
│   ├── bigquery_writer.py
│   ├── metrics.py
│   ├── pricing.py
│   ├── rules.py
│   ├── schema.py
│   └── trends.py
└── outputs/
```

## Requirements

- Python 3.11+
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

## Configuration

Create a `.env` file in the project root:

```ini
GCP_PROJECT_ID=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/gcp-key.json
BIGQUERY_DATASET=finops_agent
GEMINI_API_KEY=your-api-key
GEMINI_MODEL=gemini-2.5-flash
```

Notes:

- `GOOGLE_APPLICATION_CREDENTIALS` can be omitted if `gcp-key.json` is placed in the repository root
- `BIGQUERY_DATASET` is optional
- `GEMINI_API_KEY` is optional; without it, report generation uses deterministic fallback

## Usage

Run the full pipeline in this order:

```bash
./venv/bin/python collector.py
./venv/bin/python summarizer.py
./venv/bin/python quality_check.py
./venv/bin/python emailer.py
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

Run all tests with:

```bash
./venv/bin/python -m unittest discover -s tests -v
```

Current expected result:

- `Ran 15 tests`
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
