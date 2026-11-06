# Backend error alerts. The app writes Error Reporting–ready JSON logs on Cloud Run
# (sombrero/src/kavach/logs.py), so errors are grouped in Error Reporting automatically.
# This adds an email whenever the sombrero service logs errors, so failures like the
# hearing's silent coaching bug are seen within minutes instead of in a live demo.

resource "google_logging_metric" "sombrero_errors" {
  name   = "sombrero_errors"
  filter = <<-EOT
    resource.type="cloud_run_revision"
    resource.labels.service_name="sombrero"
    severity>=ERROR
  EOT
  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    unit        = "1"
  }
  depends_on = [google_project_service.apis]
}

resource "google_monitoring_notification_channel" "email" {
  count        = var.alert_email == "" ? 0 : 1
  display_name = "Kavach backend errors"
  type         = "email"
  labels       = { email_address = var.alert_email }
  depends_on   = [google_project_service.apis]
}

resource "google_monitoring_alert_policy" "sombrero_errors" {
  count        = var.alert_email == "" ? 0 : 1
  display_name = "sombrero is logging errors"
  combiner     = "OR"

  conditions {
    display_name = "Any error in 5 minutes"
    condition_threshold {
      filter          = "metric.type=\"logging.googleapis.com/user/${google_logging_metric.sombrero_errors.name}\" AND resource.type=\"cloud_run_revision\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      duration        = "0s"
      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_SUM"
      }
      trigger { count = 1 }
    }
  }

  # One email per incident; it closes itself after 30 quiet minutes.
  alert_strategy { auto_close = "1800s" }

  documentation {
    content   = "sombrero logged errors. Open Error Reporting for the grouped stack traces: https://console.cloud.google.com/errors?project=${var.project_id}"
    mime_type = "text/markdown"
  }

  notification_channels = [google_monitoring_notification_channel.email[0].id]
}
