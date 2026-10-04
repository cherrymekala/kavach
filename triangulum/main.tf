terraform {
  required_providers {
    google = { source = "hashicorp/google", version = "~> 6.0" }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region

  # Billing Budgets API rejects user ADC without a quota project.
  billing_project       = var.project_id
  user_project_override = true
}

locals {
  apis = [
    "cloudresourcemanager.googleapis.com", "run.googleapis.com", "aiplatform.googleapis.com", "firestore.googleapis.com",
    "storage.googleapis.com", "discoveryengine.googleapis.com", "bigquery.googleapis.com",
    "cloudscheduler.googleapis.com", "secretmanager.googleapis.com", "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com", "dlp.googleapis.com", "billingbudgets.googleapis.com", "firebaserules.googleapis.com",
  ]
}

resource "google_project_service" "apis" {
  for_each           = toset(local.apis)
  service            = each.value
  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "kavach" {
  location      = var.region
  repository_id = "kavach"
  format        = "DOCKER"
  depends_on    = [google_project_service.apis]
}

resource "google_storage_bucket" "docs" {
  name                        = "${var.project_id}-docs"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  # Case documents are deleted by the app 30 days after a case is resolved (or at once when the
  # patient deletes the case). This is only a backstop for abandoned cases: 18 months covers the
  # longest dispute path (India: one year to reach the Ombudsman + 90 days for its decision).
  lifecycle_rule {
    condition { age = 548 }
    action { type = "Delete" }
  }
  # Batch-labelling working files.
  lifecycle_rule {
    condition {
      age            = 30
      matches_prefix = ["batch/"]
    }
    action { type = "Delete" }
  }
}

resource "google_firestore_database" "default" {
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"
  depends_on  = [google_project_service.apis]
}

resource "google_service_account" "run" {
  account_id   = "sombrero-run"
  display_name = "Kavach API on Cloud Run"
}

resource "google_project_iam_member" "run_roles" {
  for_each = toset([
    "roles/datastore.user", "roles/storage.objectAdmin", "roles/aiplatform.user",
    "roles/discoveryengine.user", "roles/bigquery.dataEditor", "roles/secretmanager.secretAccessor",
  ])
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.run.email}"
}

resource "google_service_account" "build" {
  account_id   = "kavach-build"
  display_name = "Cloud Build deployer for Kavach"
}

resource "google_project_iam_member" "build_roles" {
  for_each = toset([
    # run.admin (not run.developer) so the deploy can set --allow-unauthenticated.
    "roles/run.admin", "roles/artifactregistry.writer", "roles/logging.logWriter",
  ])
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.build.email}"
}

resource "google_service_account_iam_member" "build_acts_as_run" {
  service_account_id = google_service_account.run.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.build.email}"
}

data "google_project" "this" {}

resource "google_billing_budget" "cap" {
  billing_account = var.billing_account
  display_name    = "kavach-budget"
  budget_filter { projects = ["projects/${data.google_project.this.number}"] }
  amount {
    specified_amount {
      currency_code = var.budget_currency
      units         = tostring(var.budget_amount)
    }
  }
  threshold_rules { threshold_percent = 0.5 }
  threshold_rules { threshold_percent = 0.9 }
  threshold_rules { threshold_percent = 1.0 }
}


# Past rulings for "similar cases". Vertex AI Search only offers global/us/eu, so it holds
# public rulings only; patient documents stay in the asia-south1 bucket.
resource "google_discovery_engine_data_store" "rulings" {
  location          = "global"
  data_store_id     = "kavach-rulings"
  display_name      = "Kavach rulings"
  industry_vertical = "GENERIC"
  content_config    = "CONTENT_REQUIRED"
  solution_types    = ["SOLUTION_TYPE_SEARCH"]
  depends_on        = [google_project_service.apis]
  lifecycle {
    # Google fills in a default parsing config; changing it forces a replace, which would
    # wipe the 3,120 imported rulings.
    ignore_changes  = [document_processing_config]
    prevent_destroy = true
  }
}

resource "google_discovery_engine_search_engine" "rulings" {
  engine_id      = "kavach-rulings"
  collection_id  = "default_collection"
  location       = google_discovery_engine_data_store.rulings.location
  display_name   = "Kavach rulings search"
  data_store_ids = [google_discovery_engine_data_store.rulings.data_store_id]
  search_engine_config {
    search_tier = "SEARCH_TIER_STANDARD"
  }
}

output "rulings_engine" {
  value = google_discovery_engine_search_engine.rulings.engine_id
}


# Daily escalation tracker. The API is public, so /tracker/tick only accepts an OIDC token
# issued to this service account (checked in routers/tracker.py).
resource "google_service_account" "scheduler" {
  account_id   = "kavach-scheduler"
  display_name = "Kavach daily tracker (Cloud Scheduler)"
}

data "google_cloud_run_v2_service" "sombrero" {
  name     = "sombrero"
  location = var.region
}

resource "google_cloud_scheduler_job" "tracker" {
  name        = "kavach-tracker-tick"
  region      = var.region
  schedule    = "0 9 * * *"
  time_zone   = "Asia/Kolkata"
  description = "Escalate cases whose dispute deadline passed; warn on the Ombudsman one-year limit."
  retry_config {
    retry_count = 2
  }
  http_target {
    http_method = "POST"
    uri         = "${data.google_cloud_run_v2_service.sombrero.uri}/tracker/tick"
    oidc_token {
      service_account_email = google_service_account.scheduler.email
      audience              = "${data.google_cloud_run_v2_service.sombrero.uri}/tracker/tick"
    }
  }
  depends_on = [google_project_service.apis]
}

# Firestore security rules: owners can read their own case; no client writes.
resource "google_firebaserules_ruleset" "firestore" {
  project = var.project_id
  source {
    files {
      name    = "firestore.rules"
      content = file("${path.module}/firestore.rules")
    }
  }
  depends_on = [google_firestore_database.default, google_project_service.apis]
}

resource "google_firebaserules_release" "firestore" {
  project      = var.project_id
  name         = "cloud.firestore"
  ruleset_name = google_firebaserules_ruleset.firestore.name
}
