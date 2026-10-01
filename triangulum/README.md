# triangulum: Google Cloud infrastructure (Terraform)

```bash
cd triangulum
cp terraform.tfvars.example terraform.tfvars   # set project_id and billing email
terraform init && terraform apply
```

Creates: APIs, Artifact Registry, Cloud Storage bucket (30-day delete), Firestore, service account for Cloud Run, Cloud Scheduler job, and a budget alert.

Cost rules: Cloud Run min instances 0 (set 1 only during judging), no VMs, no GPUs, small Vertex AI Search index.
