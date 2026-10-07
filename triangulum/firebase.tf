# Firebase for the web app (andromeda/web): project, web app, phone sign-in, hosting site.

variable "auth_test_phone_numbers" {
  description = "Fictional numbers that sign in with a fixed code and never send an SMS (demo/judging)."
  type        = map(string)
  default = {
    "+919999900001" = "123456"
    "+919999900002" = "123456"
    "+6580000001"   = "123456"
  }
}

resource "google_project_service" "firebase" {
  for_each = toset([
    "firebase.googleapis.com", "identitytoolkit.googleapis.com", "firebasehosting.googleapis.com",
  ])
  service            = each.value
  disable_on_destroy = false
}

resource "google_firebase_project" "default" {
  provider   = google-beta
  project    = var.project_id
  depends_on = [google_project_service.firebase]
}

resource "google_firebase_web_app" "kavach" {
  provider     = google-beta
  project      = var.project_id
  display_name = "Kavach web"
  depends_on   = [google_firebase_project.default]
}

data "google_firebase_web_app_config" "kavach" {
  provider   = google-beta
  project    = var.project_id
  web_app_id = google_firebase_web_app.kavach.app_id
}

# Firebase Auth (Identity Platform): phone OTP only.
resource "google_identity_platform_config" "auth" {
  project = var.project_id
  sign_in {
    allow_duplicate_emails = false
    phone_number {
      enabled            = true
      test_phone_numbers = var.auth_test_phone_numbers
    }
  }
  # Identity Platform defaulted to "allowlist only" with an empty list, which blocks every
  # country and surfaces in the app as auth/operation-not-allowed. Allow our launch markets.
  sms_region_config {
    allowlist_only {
      allowed_regions = ["IN", "SG"]
    }
  }
  authorized_domains = [
    "localhost",
    "${var.project_id}.firebaseapp.com",
    "${var.project_id}.web.app",
  ]
  depends_on = [google_firebase_project.default]
}

resource "google_firebase_hosting_site" "web" {
  provider = google-beta
  project  = var.project_id
  site_id  = var.project_id
  app_id   = google_firebase_web_app.kavach.app_id
}

# Public by design: Firebase web config is shipped to every browser. Access is enforced by
# Firestore rules, Auth and the API's token checks, not by hiding these values.
output "firebase_web_env" {
  value = <<-ENV
    VITE_API_URL=${data.google_cloud_run_v2_service.sombrero.uri}
    VITE_FIREBASE_API_KEY=${data.google_firebase_web_app_config.kavach.api_key}
    VITE_FIREBASE_AUTH_DOMAIN=${data.google_firebase_web_app_config.kavach.auth_domain}
    VITE_FIREBASE_PROJECT_ID=${var.project_id}
    VITE_FIREBASE_APP_ID=${google_firebase_web_app.kavach.app_id}
    VITE_FIREBASE_MESSAGING_SENDER_ID=${data.google_firebase_web_app_config.kavach.messaging_sender_id}
    VITE_FIREBASE_STORAGE_BUCKET=${data.google_firebase_web_app_config.kavach.storage_bucket}
  ENV
}
