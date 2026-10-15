# ==============================================================================
# Clinical Triage Agent - Google Cloud Infrastructure as Code (Terraform)
# Provisions:
# 1. Cloud Secret Manager (API keys, clinical backend credentials)
# 2. Artifact Registry (Container images)
# 3. Cloud Trace / OpenTelemetry permissions
# 4. Service Account & IAM Roles (Least Privilege)
# ==============================================================================

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

variable "project_id" {
  type        = string
  description = "GCP Project ID"
  default     = "jimbo-agy"
}

variable "region" {
  type        = string
  description = "GCP Region for Agent Runtime and Artifact Registry"
  default     = "us-central1"
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# 1. Service Account for Agent Runtime execution
resource "google_service_account" "agent_runner" {
  account_id   = "clinical-triage-agent-sa"
  display_name = "Clinical Triage Agent Runtime Service Account"
  description  = "Least-privilege service account executing the clinical triage graph workflow"
}

# 2. Secret Manager for Secure Clinical API Credentials (No hardcoding)
resource "google_secret_manager_secret" "clinical_emr_api_key" {
  secret_id = "clinical-emr-api-key"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_iam_member" "agent_secret_accessor" {
  secret_id = google_secret_manager_secret.clinical_emr_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.agent_runner.email}"
}

# 3. Artifact Registry for Container Deployment
resource "google_artifact_registry_repository" "agent_repo" {
  location      = var.region
  repository_id = "clinical-triage-repo"
  description   = "Docker container repository for clinical-triage-agent"
  format        = "DOCKER"
}

# 4. Cloud Trace IAM binding for OpenTelemetry Tracing
resource "google_project_iam_member" "trace_agent" {
  project = var.project_id
  role    = "roles/cloudtrace.agent"
  member  = "serviceAccount:${google_service_account.agent_runner.email}"
}

# 5. Vertex AI User IAM binding
resource "google_project_iam_member" "vertex_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.agent_runner.email}"
}

output "service_account_email" {
  value       = google_service_account.agent_runner.email
  description = "Email of the provisioned agent runtime service account"
}

output "artifact_registry_repository_id" {
  value       = google_artifact_registry_repository.agent_repo.id
  description = "Artifact Registry Repository URI"
}
