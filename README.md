# COMP0239 Coursework: Distributed Spark Analysis Pipeline

A distributed computing pipeline that provisions cloud infrastructure, deploys an Apache Spark cluster, and runs LLM-based software engineering analysis at scale.

## Overview

This project automates the deployment of a complete data analysis environment on UCL's Harvester cloud infrastructure:

| Component | Purpose |
|-----------|---------|
| **Terraform** | Infrastructure provisioning (VMs, networking) |
| **Ansible** | Configuration management and service deployment |
| **Apache Spark** | Distributed data processing |
| **MinIO** | S3-compatible object storage for results |
| **Prometheus + Grafana** | Monitoring and visualization |
| **SWE-LLaMA** | LLM for software engineering analysis |

## Project Structure

```
.
├── terraform/              # Infrastructure as Code
│   ├── main.tf             # VM and resource definitions
│   ├── variables.tf        # Configurable parameters
│   └── outputs.tf          # Exported values
├── ansible/                # Configuration playbooks
│   ├── site.yaml           # Main orchestration playbook
│   ├── spark-*.yaml        # Spark cluster setup
│   ├── minio-*.yaml        # MinIO storage setup
│   ├── prometheus-*.yaml   # Monitoring setup
│   └── run_spark_swe_llama.py  # Analysis script
└── generate_inventory.py   # Dynamic Ansible inventory
```

## Prerequisites

- Terraform >= 1.0
- Ansible >= 2.9
- SSH key configured for Harvester access
- Access to UCL's Harvester namespace

---

## Quick Start

> All commands should be run from the project root directory.

### 1. Provision Infrastructure

```bash
cd terraform/
terraform init
terraform apply -auto-approve
cd ..
```

### 2. Configure Nodes & Start Services

```bash
ansible-playbook ansible/site.yaml \
  -i generate_inventory.py \
  --private-key ~/.ssh/id_ed25519
```

### 3. Run Analysis Job

```bash
ansible-playbook ansible/run-analysis.yaml \
  -i generate_inventory.py \
  --private-key ~/.ssh/id_ed25519
```

> The job runs asynchronously. Monitor progress via the Spark UI.

---

## Web Interfaces

| Service | URL | Credentials |
|---------|-----|-------------|
| **MinIO Console** | `http://ucabroy-minio-console.condenser.ucl.ac.uk` | `guiuser` / `abcd1234` |
| **MinIO S3 API** | `http://ucabroy-minio-s3.condenser.ucl.ac.uk` | — |
| **Spark Master UI** | `http://ucabroy-spark-master-ui.condenser.ucl.ac.uk` | — |
| **Spark App UI** | `http://ucabroy-spark-app-ui.condenser.ucl.ac.uk` | — |
| **Grafana** | `https://ucabroy-cw-grafana.condenser.ucl.ac.uk` | `admin` / `admin` |
| **Prometheus** | `https://ucabroy-cw-prometheus.condenser.ucl.ac.uk` | — |

## Accessing Results

Analysis results are stored in MinIO under the `analysis-results` bucket. Access via:

- **Web UI**: MinIO Console (see table above)
- **CLI**: Use `mc` (MinIO Client) with the S3 endpoint
- **Programmatic**: S3A connector in Spark applications

---

## Cleanup

Destroy all provisioned infrastructure:

```bash
cd terraform/
terraform destroy -auto-approve
cd ..
```

---

## Configuration

Key parameters can be modified in `terraform/variables.tf`:

| Variable | Default | Description |
|----------|---------|-------------|
| `vm_count` | 3 | Number of VMs to provision |
| `namespace` | `ucabroy-comp0235-ns` | Harvester namespace |
| `username` | `ucabroy` | SSH username |