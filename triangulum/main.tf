terraform {
  required_providers {
    google = { source = "hashicorp/google", version = "~> 6.0" }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  apis = [
    "run.googleapis.com", "aiplatform.googleapis.com", "firestore.googleapis.com",
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

resource "google_billing_budget" "cap" {
  billing_account = var.billing_account
  display_name    = "kavach-budget"
  budget_filter { projects = ["projects/${var.project_id}"] }
  amount {
    specified_amount {
      currency_code = "USD"
      units         = tostring(var.budget_usd)
    }
  }
  threshold_rules { threshold_percent = 0.5 }
  threshold_rules { threshold_percent = 0.9 }
  threshold_rules { threshold_percent = 1.0 }
}

# Cloud Scheduler job for /tracker/tick: add after the first Cloud Run deploy, when the URL exists.
