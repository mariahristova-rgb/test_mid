# Offline vendor plan controls only: all provider operations are mocked.
# Fixture budget/approval values do not authorize any real resource or expense.
mock_provider "google" {}
override_resource {
  target          = google_service_account.api
  values          = { email = "phase26d-api@example.invalid" }
  override_during = plan
}
variables {
  project_id             = "synthetic-phase26d"
  project_number         = "123456789"
  billing_account_id     = "000000-000000-000000"
  monthly_budget_usd     = 1
  region                 = "us-central1"
  api_image              = "example.invalid/api@sha256:0000000000000000000000000000000000000000000000000000000000000000"
  model_image            = "example.invalid/model@sha256:1111111111111111111111111111111111111111111111111111111111111111"
  postgres_dsn_secret_id = "synthetic-dsn"
  encryption_secret_id   = "synthetic-encryption"
}
run "missing_approval_is_rejected" {
  command = plan
  variables { apply_authorized = false }
  expect_failures = [google_compute_network.staging]
}
run "bounded_private_mock_plan" {
  command = plan
  variables { apply_authorized = true }
  assert {
    condition     = google_cloud_run_v2_service.model.ingress == "INGRESS_TRAFFIC_INTERNAL_ONLY"
    error_message = "Model ingress must remain private."
  }
  assert {
    condition     = google_cloud_run_v2_service_iam_member.invoke.member == "serviceAccount:${google_service_account.api.email}" && google_cloud_run_v2_service_iam_member.invoke.role == "roles/run.invoker"
    error_message = "Only the dedicated API principal may invoke inference."
  }
  assert {
    condition     = google_cloud_run_v2_service.model.template[0].scaling[0].max_instance_count == 1 && google_cloud_run_v2_service.model.template[0].scaling[0].min_instance_count == 0
    error_message = "Inference allocations must be bounded and cold by default."
  }
  assert {
    condition     = google_sql_database_instance.staging.settings[0].ip_configuration[0].ipv4_enabled == false && google_sql_database_instance.staging.settings[0].backup_configuration[0].enabled == true
    error_message = "SQL requires private routing and backups."
  }
  assert {
    condition     = google_storage_bucket.files.public_access_prevention == "enforced" && google_storage_bucket.files.uniform_bucket_level_access
    error_message = "Tenant files cannot use public bucket ACLs."
  }
}
run "unpinned_api_image_is_rejected" {
  command = plan
  variables {
    apply_authorized = true
    api_image        = "example.invalid/api:latest"
  }
  expect_failures = [var.api_image]
}
