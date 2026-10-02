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
    "artifactregistry.googleapis.com", "dlp.googleapis.com", "billingbudgets.googleapis.com",
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
  lifecycle_rule {
    condition { age = 30 }
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

# Cloud Scheduler job for /tracker/tick: add after the first Cloud Run deploy, when the URL exists.

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

