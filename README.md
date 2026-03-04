# FinOps-AI-Agent 🚀

**An intelligent, AI-driven SRE assistant for autonomous cloud cost optimization.**

## Overview

Keeping cloud estates lean in 2026 is as critical as keeping them reliable. FinOps-AI-Agent bridges traditional SRE observability with FinOps discipline: it discovers Google Cloud resources, profiles their utilization, and packages telemetry so downstream LLM workflows can recommend right-sizing or automation actions.

## Architecture Snapshot

| Phase                                 | Status      | Highlights                                                                                  |
| ------------------------------------- | ----------- | ------------------------------------------------------------------------------------------- |
| Phase 1 – Real-time Metrics Collector | ✅ Complete | Multi-zone GCE discovery, metadata capture, CPU utilization ingestion, JSON export for LLMs |
| Phase 2 – LLM Insights                | 🛠 Planned  | Correlate metrics with GCP pricing, generate optimization narratives                        |
| Phase 3 – Alerting & Collaboration    | 🛠 Planned  | Slack/Email alerts with remediation playbooks                                               |
| Phase 4 – Self-healing GitOps Loop    | 🛠 Planned  | Auto-create Terraform PRs to resize or schedule instances                                   |

## Tech Stack

- **Cloud:** Google Cloud Platform (Compute Engine, Cloud Monitoring)
- **Language:** Python 3.11
- **Auth:** IAM Service Accounts (least-privilege)
- **AI Tooling (planned):** Google Gemini API, LangChain

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

### Configuration

1. Place `gcp-key.json` in the project root.
2. Create a `.env` file (auto-loaded by `collector.py`):
   ```ini
   GCP_PROJECT_ID=your-project-id
   GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/gcp-key.json  # optional; auto-set if omitted
   ```

### Run the Metrics Collector

```bash
./venv/bin/python collector.py
```

The script:

1. Loads variables from `.env`.
2. Ensures Google Application Default Credentials point to `gcp-key.json` (or respects your manual setting).
3. Discovers all Compute Engine instances across zones.
4. Fetches the past hour of CPU utilization (5-minute samples) via Cloud Monitoring.
5. Prints a styled terminal table and writes `metrics.json` for downstream AI agents.

## Output

- **Terminal:** colorized table summarizing instance name, machine type, zone, and CPU%.
- **File:** `metrics.json` – structured telemetry ready for LLM ingestion.

## Roadmap

- [x] Milestone 1: Robust GCP metrics collector.
- [ ] Milestone 2: LLM analysis against GCP pricing data.
- [ ] Milestone 3: Automated alerting to Slack/Email.
- [ ] Milestone 4: GitOps-based self-healing (Terraform PRs for resizing/shutdown).

## Contributing

Issues and PRs are welcome—please document environment assumptions and include reproduction steps for any bug reports.
