# Retrieval Eval Report

- Total cases: 10
- Passed: 10
- Pass rate: 1.0
- Topic hit rate: 1.0
- Doc hit rate: 1.0
- Usage hit rate: 1.0
- Top-k: 5

## Rank Metrics

- Top-1 topic hit rate: 1.0
- Top-1 doc hit rate: 1.0
- Top-1 usage hit rate: 1.0
- Top-3 topic hit rate: 1.0
- Top-3 doc hit rate: 1.0
- Top-3 usage hit rate: 1.0
- Top-5 topic hit rate: 1.0
- Top-5 doc hit rate: 1.0
- Top-5 usage hit rate: 1.0

## Cases

### labels_add - PASS

- Query: `how to add labels to compute engine resources`
- Topic hit: `True`
- Doc hit: `True`
- Usage hit: `True`
- Top-1: topic=`True` doc=`True` usage=`True`
- Top-3: topic=`True` doc=`True` usage=`True`
- Top-5: topic=`True` doc=`True` usage=`True`
- Top results:
  - `Use labels on Compute Engine` | topic=`labels` | doc=`compute-labels` | score=`0.7764`
  - `Create resources with labels - gcloud` | topic=`labels` | doc=`compute-labels` | score=`0.7554`
  - `Add or update labels - REST [chunk 2/2]` | topic=`labels` | doc=`compute-labels` | score=`0.6886`

### labels_filter - PASS

- Query: `how to filter compute engine resources by labels`
- Topic hit: `True`
- Doc hit: `True`
- Usage hit: `True`
- Top-1: topic=`True` doc=`True` usage=`True`
- Top-3: topic=`True` doc=`True` usage=`True`
- Top-5: topic=`True` doc=`True` usage=`True`
- Top results:
  - `Filter searches using labels - console` | topic=`labels` | doc=`compute-labels` | score=`0.7441`
  - `View labels - gcloud (part 5) [chunk 1/2]` | topic=`labels` | doc=`compute-labels` | score=`0.7155`
  - `Use labels on Compute Engine` | topic=`labels` | doc=`compute-labels` | score=`0.6981`

### dataset_terraform - PASS

- Query: `how to create a dataset with terraform`
- Topic hit: `True`
- Doc hit: `True`
- Usage hit: `True`
- Top-1: topic=`True` doc=`True` usage=`True`
- Top-3: topic=`True` doc=`True` usage=`True`
- Top-5: topic=`True` doc=`True` usage=`True`
- Top results:
  - `Create datasets - Terraform (part 4) [chunk 2/2]` | topic=`bigquery-datasets` | doc=`bigquery-datasets` | score=`0.6961`
  - `Create datasets - Terraform (part 1) [chunk 2/3]` | topic=`bigquery-datasets` | doc=`bigquery-datasets` | score=`0.6514`
  - `Create datasets - Terraform (part 1) [chunk 3/3]` | topic=`bigquery-datasets` | doc=`bigquery-datasets` | score=`0.6468`

### dataset_sql - PASS

- Query: `how to create a dataset with sql in bigquery`
- Topic hit: `True`
- Doc hit: `True`
- Usage hit: `True`
- Top-1: topic=`True` doc=`True` usage=`True`
- Top-3: topic=`True` doc=`True` usage=`True`
- Top-5: topic=`True` doc=`True` usage=`True`
- Top results:
  - `Create datasets - SQL (part 1) [chunk 1/3]` | topic=`bigquery-datasets` | doc=`bigquery-datasets` | score=`0.6919`
  - `Create datasets - console (part 1) [chunk 1/2]` | topic=`bigquery-datasets` | doc=`bigquery-datasets` | score=`0.6917`
  - `Required permissions (part 18) [chunk 2/2]` | topic=`bigquery-datasets` | doc=`bigquery-datasets` | score=`0.69`

### ops_install_linux - PASS

- Query: `how to install the ops agent on linux`
- Topic hit: `True`
- Doc hit: `True`
- Usage hit: `True`
- Top-1: topic=`True` doc=`True` usage=`True`
- Top-3: topic=`True` doc=`True` usage=`True`
- Top-5: topic=`True` doc=`True` usage=`True`
- Top results:
  - `Install the agent automatically during VM creation` | topic=`ops-agent` | doc=`ops-agent-installation` | score=`0.7583`
  - `VMs without remote package access` | topic=`ops-agent` | doc=`ops-agent-installation` | score=`0.7384`
  - `Install specific Ops Agent version - Windows (part 7) [chunk 2/2]` | topic=`ops-agent` | doc=`ops-agent-installation` | score=`0.7063`

### ops_install_windows - PASS

- Query: `how to install the ops agent on windows`
- Topic hit: `True`
- Doc hit: `True`
- Usage hit: `True`
- Top-1: topic=`True` doc=`True` usage=`True`
- Top-3: topic=`True` doc=`True` usage=`True`
- Top-5: topic=`True` doc=`True` usage=`True`
- Top results:
  - `Install the agent automatically during VM creation` | topic=`ops-agent` | doc=`ops-agent-installation` | score=`0.773`
  - `Install specific Ops Agent version - Windows (part 7) [chunk 2/2]` | topic=`ops-agent` | doc=`ops-agent-installation` | score=`0.7283`
  - `Install the agent from the command line` | topic=`ops-agent` | doc=`ops-agent-installation` | score=`0.7057`

### memory_telemetry - PASS

- Query: `why is memory telemetry missing on a vm`
- Topic hit: `True`
- Doc hit: `True`
- Usage hit: `True`
- Top-1: topic=`True` doc=`True` usage=`True`
- Top-3: topic=`True` doc=`True` usage=`True`
- Top-5: topic=`True` doc=`True` usage=`True`
- Top results:
  - `Install specific Ops Agent version - Windows (part 8) [chunk 1/2]` | topic=`ops-agent` | doc=`ops-agent-installation` | score=`0.4715`
  - `Install specific Ops Agent version - Windows (part 6) [chunk 1/2]` | topic=`ops-agent` | doc=`ops-agent-installation` | score=`0.44`
  - `Monitoring features (part 3) [chunk 2/2]` | topic=`ops-agent` | doc=`ops-agent-overview` | score=`0.3822`

### cpu_metric - PASS

- Query: `what metric shows compute engine cpu utilization`
- Topic hit: `True`
- Doc hit: `True`
- Usage hit: `True`
- Top-1: topic=`True` doc=`True` usage=`True`
- Top-3: topic=`True` doc=`True` usage=`True`
- Top-5: topic=`True` doc=`True` usage=`True`
- Top results:
  - `Compute Engine CPU utilization metric` | topic=`gcp-compute-metrics` | doc=`gcp-metrics-catalog` | score=`0.6954`
  - `Compute metrics catalog overview` | topic=`gcp-compute-metrics` | doc=`gcp-metrics-catalog` | score=`0.567`
  - `Guest CPU usage time metric` | topic=`gcp-compute-metrics` | doc=`gcp-metrics-catalog` | score=`0.5639`

### machine_types - PASS

- Query: `how to compare compute engine machine types for rightsizing`
- Topic hit: `True`
- Doc hit: `True`
- Usage hit: `True`
- Top-1: topic=`True` doc=`True` usage=`True`
- Top-3: topic=`True` doc=`True` usage=`True`
- Top-5: topic=`True` doc=`True` usage=`True`
- Top results:
  - `Accelerator-optimized machine family guide (part 3) [chunk 2/2]` | topic=`machine-types` | doc=`compute-machine-types` | score=`0.6328`
  - `Accelerator-optimized machine family guide (part 3) [chunk 1/2]` | topic=`machine-types` | doc=`compute-machine-types` | score=`0.6094`
  - `Machine families resource and comparison guide  |  Compute Engine  |  Google Cloud Documentation overview (part 1) [chunk 1/2]` | topic=`machine-types` | doc=`compute-machine-types` | score=`0.5892`

### labels_cost_center - PASS

- Query: `why should i use owner and cost center labels`
- Topic hit: `True`
- Doc hit: `True`
- Usage hit: `True`
- Top-1: topic=`True` doc=`True` usage=`True`
- Top-3: topic=`True` doc=`True` usage=`True`
- Top-5: topic=`True` doc=`True` usage=`True`
- Top results:
  - `Common uses of labels [chunk 1/2]` | topic=`labels` | doc=`compute-labels` | score=`0.6379`
  - `What are labels?` | topic=`labels` | doc=`compute-labels` | score=`0.4624`
  - `Common uses of labels [chunk 2/2]` | topic=`labels` | doc=`compute-labels` | score=`0.3376`

