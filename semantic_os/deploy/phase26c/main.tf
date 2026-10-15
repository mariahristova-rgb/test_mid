terraform {

  required_version = ">= 1.9, < 2.0"
  required_providers {

    google = {
      source = "hashicorp/google", version = "~> 6.0"
    }


  }


}

provider "google" {
  project = var.project_id
  region  = var.region

}

variable "project_id" {
  type    = string
  default = "strong-keel-468007-r7"

}

variable "region" {
  type    = string
  default = "us-central1"

}

variable "apply_authorized" {
  type    = bool
  default = false

}

variable "api_image" {
  type = string
  validation {
    condition     = can(regex("@sha256:[0-9a-f]{64}$", var.api_image))
    error_message = "A reviewed immutable API image digest is required."

  }


}

variable "model_image" {
  type = string
  validation {
    condition     = can(regex("@sha256:[0-9a-f]{64}$", var.model_image))
    error_message = "A reviewed immutable inference image digest is required."

  }


}

variable "postgres_dsn_secret_id" {
  type = string
}

variable "encryption_secret_id" {
  type = string
}

resource "google_compute_network" "staging" {

  name                    = "ontelyx-phase26c"
  auto_create_subnetworks = false
  lifecycle {
    precondition {
      condition     = var.apply_authorized && var.billing_account_id != "" && var.monthly_budget_usd > 0
      error_message = "STOP: exact resource, financial and deployment approval required."

    }

  }


}

resource "google_compute_subnetwork" "staging" {

  name                     = "ontelyx-phase26c"
  ip_cidr_range            = "10.26.0.0/24"
  network                  = google_compute_network.staging.id
  private_ip_google_access = true

}

resource "google_compute_global_address" "sql_range" {

  name          = "ontelyx-phase26c-sql"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.staging.id

}

resource "google_service_networking_connection" "sql" {

  network                 = google_compute_network.staging.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.sql_range.name]

}

resource "google_service_account" "api" {

  account_id   = "ontelyx-phase26c-api"
  display_name = "Isolated staging API"

}

resource "google_service_account" "model" {

  account_id   = "ontelyx-phase26c-model"
  display_name = "Private inference only"

}

resource "google_sql_database_instance" "staging" {

  name                = "ontelyx-phase26c"
  region              = var.region
  database_version    = "POSTGRES_17"
  deletion_protection = true
  depends_on          = [google_service_networking_connection.sql]
  settings {

    tier              = "db-custom-1-3840"
    disk_size         = 20
    disk_autoresize   = false
    availability_type = "ZONAL"
    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = 7

    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.staging.id
      ssl_mode        = "ENCRYPTED_ONLY"

    }

    database_flags {
      name  = "cloudsql.iam_authentication"
      value = "on"

    }


  }


}

resource "google_sql_database" "assistant" {

  name     = "assistant"
  instance = google_sql_database_instance.staging.name

}

resource "google_storage_bucket" "files" {

  name                        = "${var.project_id}-ontelyx-phase26c-files"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 30
    }

    action {
      type = "Delete"
    }


  }


}

resource "google_storage_bucket" "models" {

  name                        = "${var.project_id}-ontelyx-phase26c-models"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

}

resource "google_storage_bucket_iam_member" "model_read" {

  bucket = google_storage_bucket.models.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.model.email}"

}

resource "google_project_iam_member" "sql_client" {

  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.api.email}"

}

resource "google_secret_manager_secret_iam_member" "dsn" {

  secret_id = var.postgres_dsn_secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api.email}"

}

resource "google_secret_manager_secret_iam_member" "encryption" {

  secret_id = var.encryption_secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api.email}"

}

resource "google_cloud_run_v2_service" "model" {

  name                = "ontelyx-phase26c-inference"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_INTERNAL_ONLY"
  deletion_protection = true
  template {

    service_account                  = google_service_account.model.email
    timeout                          = "60s"
    max_instance_request_concurrency = 4
    gpu_zonal_redundancy_disabled    = true
    scaling {
      min_instance_count = 0
      max_instance_count = 1

    }

    node_selector {
      accelerator = "nvidia-l4"
    }

    containers {

      image = var.model_image
      resources {
        limits = {
          cpu = "4", memory = "16Gi", "nvidia.com/gpu" = "1"
        }

        cpu_idle = false

      }

      startup_probe {
        http_get {
          path = "/health"
        }

        failure_threshold = 30
        period_seconds    = 10

      }


    }


  }


}

resource "google_cloud_run_v2_service_iam_member" "invoke" {

  name     = google_cloud_run_v2_service.model.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.api.email}"

}

resource "google_cloud_run_v2_service" "api" {

  name                = "ontelyx-phase26c-api"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = true
  template {

    service_account                  = google_service_account.api.email
    timeout                          = "60s"
    max_instance_request_concurrency = 4
    scaling {
      min_instance_count = 0
      max_instance_count = 1

    }

    vpc_access {
      egress = "PRIVATE_RANGES_ONLY"
      network_interfaces {
        network    = google_compute_network.staging.name
        subnetwork = google_compute_subnetwork.staging.name

      }


    }

    containers {

      image = var.api_image
      resources {
        limits = {
          cpu = "2", memory = "2Gi"
        }

      }

      env {
        name  = "ASSISTANT_ENV"
        value = "staging"

      }

      env {
        name  = "ASSISTANT_STORAGE_BACKEND"
        value = "postgresql"

      }

      env {
        name  = "ASSISTANT_POSTGRES_POOL_SIZE"
        value = "4"

      }

      env {
        name  = "ASSISTANT_CUSTOMER_OAUTH_ENABLED"
        value = "false"

      }

      env {
        name = "ASSISTANT_POSTGRES_DSN"
        value_source {
          secret_key_ref {
            secret  = var.postgres_dsn_secret_id
            version = "1"

          }

        }


      }

      env {
        name = "ASSISTANT_ENCRYPTION_KEY"
        value_source {
          secret_key_ref {
            secret  = var.encryption_secret_id
            version = "1"

          }

        }


      }

      startup_probe {
        http_get {
          path = "/health/ready"
        }

        failure_threshold = 10
        period_seconds    = 10

      }


    }


  }


}

# No allUsers IAM, public GPU, OAuth clients, billing activation or credentials.
# Review application authentication, file isolation and alert delivery.
# Review immutable credential/model versions before authorizing an apply.
variable "billing_account_id" {
  type    = string
  default = ""
}
variable "monthly_budget_usd" {
  type    = number
  default = 0
}
resource "google_billing_budget" "staging" {
  count           = var.billing_account_id != "" && var.monthly_budget_usd > 0 ? 1 : 0
  billing_account = var.billing_account_id
  display_name    = "Ontelyx phase26c reviewed staging"
  budget_filter {
    projects = ["projects/${var.project_number}"]
  }
  amount {
    specified_amount {
      currency_code = "USD"
      units         = tostring(ceil(var.monthly_budget_usd))
    }
  }
  threshold_rules { threshold_percent = 0.5 }
  threshold_rules { threshold_percent = 0.9 }
  threshold_rules { threshold_percent = 1.0 }
}
resource "google_monitoring_alert_policy" "api_errors" {
  display_name = "Ontelyx phase26c API 5xx"
  combiner     = "OR"
  conditions {
    display_name = "API server errors"
    condition_threshold {
      filter          = "resource.type = \"cloud_run_revision\" AND resource.label.service_name = \"ontelyx-phase26c-api\" AND metric.type = \"run.googleapis.com/request_count\" AND metric.label.response_code_class = \"5xx\""
      comparison      = "COMPARISON_GT"
      threshold_value = 5
      duration        = "60s"
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_SUM"
      }
    }
  }
  # Notification channels are intentionally unconfigured until a recipient is approved.
}
variable "project_number" {
  type = string
  validation {
    condition     = can(regex("^[0-9]+$", var.project_number))
    error_message = "The reviewed GCP project number is required for the budget filter."
  }
}
