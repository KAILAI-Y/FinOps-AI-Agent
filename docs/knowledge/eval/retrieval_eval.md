# Retrieval Eval Report

- Total cases: 10
- Passed: 10
- Pass rate: 1.0
- Topic hit rate: 1.0
- Doc hit rate: 1.0
- Usage hit rate: 1.0
- Top-k: 5

## Rank Metrics

- Top-1 topic hit rate: 0.9
- Top-1 doc hit rate: 0.8
- Top-1 usage hit rate: 0.9
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
  - `Add or update labels - console` | topic=`labels` | doc=`compute-labels` | score=`0.319`
  - `Use labels on Compute Engine` | topic=`labels` | doc=`compute-labels` | score=`0.3134`
  - `Create resources with labels - gcloud` | topic=`labels` | doc=`compute-labels` | score=`0.261`

### labels_filter - PASS

- Query: `how to filter compute engine resources by labels`
- Topic hit: `True`
- Doc hit: `True`
- Usage hit: `True`
- Top-1: topic=`True` doc=`True` usage=`True`
- Top-3: topic=`True` doc=`True` usage=`True`
- Top-5: topic=`True` doc=`True` usage=`True`
- Top results:
  - `View labels - gcloud (part 5) [chunk 1/2]` | topic=`labels` | doc=`compute-labels` | score=`0.3449`
  - `View labels - gcloud (part 7) [chunk 1/2]` | topic=`labels` | doc=`compute-labels` | score=`0.3105`
  - `Filter searches using labels - REST [chunk 2/2]` | topic=`labels` | doc=`compute-labels` | score=`0.2781`

### dataset_terraform - PASS

- Query: `how to create a dataset with terraform`
- Topic hit: `True`
- Doc hit: `True`
- Usage hit: `True`
- Top-1: topic=`True` doc=`True` usage=`True`
- Top-3: topic=`True` doc=`True` usage=`True`
- Top-5: topic=`True` doc=`True` usage=`True`
- Top results:
  - `Required permissions (part 13) [chunk 2/2]` | topic=`bigquery-datasets` | doc=`bigquery-datasets` | score=`0.3524`
  - `Create datasets - Terraform (part 5)` | topic=`bigquery-datasets` | doc=`bigquery-datasets` | score=`0.3486`
  - `Create datasets - Terraform (part 1) [chunk 2/3]` | topic=`bigquery-datasets` | doc=`bigquery-datasets` | score=`0.2472`

### dataset_sql - PASS

- Query: `how to create a dataset with sql in bigquery`
- Topic hit: `True`
- Doc hit: `True`
- Usage hit: `True`
- Top-1: topic=`True` doc=`True` usage=`True`
- Top-3: topic=`True` doc=`True` usage=`True`
- Top-5: topic=`True` doc=`True` usage=`True`
- Top results:
  - `Create datasets - SQL (part 1) [chunk 1/3]` | topic=`bigquery-datasets` | doc=`bigquery-datasets` | score=`0.3369`
  - `Required permissions (part 1) [chunk 2/2]` | topic=`bigquery-datasets` | doc=`bigquery-datasets` | score=`0.2981`
  - `Required permissions (part 18) [chunk 1/2]` | topic=`bigquery-datasets` | doc=`bigquery-datasets` | score=`0.2687`

### ops_install_linux - PASS

- Query: `how to install the ops agent on linux`
- Topic hit: `True`
- Doc hit: `True`
- Usage hit: `True`
- Top-1: topic=`True` doc=`False` usage=`True`
- Top-3: topic=`True` doc=`True` usage=`True`
- Top-5: topic=`True` doc=`True` usage=`True`
- Top results:
  - `Monitoring features (part 4) [chunk 2/3]` | topic=`ops-agent` | doc=`ops-agent-overview` | score=`0.4166`
  - `Install specific Ops Agent version - Windows (part 5) [chunk 1/2]` | topic=`ops-agent` | doc=`ops-agent-installation` | score=`0.404`
  - `Install the agent automatically during VM creation` | topic=`ops-agent` | doc=`ops-agent-installation` | score=`0.3721`

### ops_install_windows - PASS

- Query: `how to install the ops agent on windows`
- Topic hit: `True`
- Doc hit: `True`
- Usage hit: `True`
- Top-1: topic=`True` doc=`True` usage=`True`
- Top-3: topic=`True` doc=`True` usage=`True`
- Top-5: topic=`True` doc=`True` usage=`True`
- Top results:
  - `Install specific Ops Agent version - Windows (part 5) [chunk 1/2]` | topic=`ops-agent` | doc=`ops-agent-installation` | score=`0.3963`
  - `Monitoring features (part 4) [chunk 3/3]` | topic=`ops-agent` | doc=`ops-agent-overview` | score=`0.3691`
  - `Install the agent automatically during VM creation` | topic=`ops-agent` | doc=`ops-agent-installation` | score=`0.3651`

### memory_telemetry - PASS

- Query: `why is memory telemetry missing on a vm`
- Topic hit: `True`
- Doc hit: `True`
- Usage hit: `True`
- Top-1: topic=`False` doc=`False` usage=`False`
- Top-3: topic=`True` doc=`True` usage=`True`
- Top-5: topic=`True` doc=`True` usage=`True`
- Top results:
  - `Predefined machine types` | topic=`machine-types` | doc=`compute-machine-types` | score=`0.2217`
  - `Install specific Ops Agent version - Windows (part 8) [chunk 1/2]` | topic=`ops-agent` | doc=`ops-agent-installation` | score=`0.2067`
  - `General-purpose machine family guide (part 1) [chunk 1/2]` | topic=`machine-types` | doc=`compute-machine-types` | score=`0.1906`

### cpu_metric - PASS

- Query: `what metric shows compute engine cpu utilization`
- Topic hit: `True`
- Doc hit: `True`
- Usage hit: `True`
- Top-1: topic=`True` doc=`True` usage=`True`
- Top-3: topic=`True` doc=`True` usage=`True`
- Top-5: topic=`True` doc=`True` usage=`True`
- Top results:
  - `Compute Engine CPU utilization metric` | topic=`gcp-compute-metrics` | doc=`gcp-metrics-catalog` | score=`0.3242`
  - `Compute metrics catalog overview` | topic=`gcp-compute-metrics` | doc=`gcp-metrics-catalog` | score=`0.2601`
  - `Monitoring features (part 2) [chunk 1/2]` | topic=`ops-agent` | doc=`ops-agent-overview` | score=`0.1913`

### machine_types - PASS

- Query: `how to compare compute engine machine types for rightsizing`
- Topic hit: `True`
- Doc hit: `True`
- Usage hit: `True`
- Top-1: topic=`True` doc=`True` usage=`True`
- Top-3: topic=`True` doc=`True` usage=`True`
- Top-5: topic=`True` doc=`True` usage=`True`
- Top results:
  - `Accelerator-optimized machine family guide (part 3) [chunk 1/2]` | topic=`machine-types` | doc=`compute-machine-types` | score=`0.4167`
  - `Machine families resource and comparison guide  |  Compute Engine  |  Google Cloud Documentation overview (part 1) [chunk 1/2]` | topic=`machine-types` | doc=`compute-machine-types` | score=`0.3211`
  - `Local SSD machine types (part 1) [chunk 1/2]` | topic=`machine-types` | doc=`compute-machine-types` | score=`0.2644`

### labels_cost_center - PASS

- Query: `why should i use owner and cost center labels`
- Topic hit: `True`
- Doc hit: `True`
- Usage hit: `True`
- Top-1: topic=`True` doc=`True` usage=`True`
- Top-3: topic=`True` doc=`True` usage=`True`
- Top-5: topic=`True` doc=`True` usage=`True`
- Top results:
  - `Common uses of labels [chunk 1/2]` | topic=`labels` | doc=`compute-labels` | score=`0.3514`
  - `Remove a label - REST [chunk 2/2]` | topic=`labels` | doc=`compute-labels` | score=`0.1865`
  - `Remove a label - REST [chunk 1/2]` | topic=`labels` | doc=`compute-labels` | score=`0.156`

