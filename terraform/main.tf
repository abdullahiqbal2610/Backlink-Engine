provider "google" {
  project = var.project_id
  region  = var.region
}

# 1. Enable Required GCP APIs
resource "google_project_service" "run_api" {
  service = "run.googleapis.com"
  disable_on_destroy = false
}
resource "google_project_service" "artifactregistry_api" {
  service = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}
resource "google_project_service" "scheduler_api" {
  service = "cloudscheduler.googleapis.com"
  disable_on_destroy = false
}

# 2. Artifact Registry for Docker Images
resource "google_artifact_registry_repository" "repo" {
  provider      = google
  location      = var.region
  repository_id = var.docker_repo_name
  description   = "Docker repository for Gaper Backlink Engine"
  format        = "DOCKER"
  depends_on    = [google_project_service.artifactregistry_api]
}

# 3. Cloud Storage Bucket (For Browser Cookies)
resource "google_storage_bucket" "cookie_bucket" {
  name          = var.cookie_bucket_name
  location      = var.region
  force_destroy = true
  uniform_bucket_level_access = true
}

# 4. Service Account for Cloud Run
resource "google_service_account" "cloud_run_sa" {
  account_id   = "gaper-cloudrun-sa"
  display_name = "Cloud Run Service Account"
}

resource "google_project_iam_member" "sa_storage_admin" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# 5. Dashboard (Cloud Run Service)
resource "google_cloud_run_v2_service" "dashboard" {
  name     = "gaper-dashboard"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"
  
  template {
    service_account = google_service_account.cloud_run_sa.email
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.docker_repo_name}/dashboard:latest"
      
      env {
        name  = "COOKIE_BUCKET_NAME"
        value = google_storage_bucket.cookie_bucket.name
      }
      # Additional ENV variables (DB, Redis) will be set via Secret Manager or Console manually
    }
  }
  depends_on = [google_project_service.run_api]
}

# Make Dashboard Publicly Accessible
resource "google_cloud_run_service_iam_member" "public_access" {
  location = google_cloud_run_v2_service.dashboard.location
  project  = google_cloud_run_v2_service.dashboard.project
  service  = google_cloud_run_v2_service.dashboard.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# 6. Workers (Cloud Run Jobs)
resource "google_cloud_run_v2_job" "execution_router" {
  name     = "gaper-router-job"
  location = var.region

  template {
    template {
      service_account = google_service_account.cloud_run_sa.email
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.docker_repo_name}/router:latest"
        resources {
          limits = {
            cpu    = "1"
            memory = "2Gi" # Playwright needs a bit more RAM
          }
        }
        env {
          name  = "COOKIE_BUCKET_NAME"
          value = google_storage_bucket.cookie_bucket.name
        }
      }
    }
  }
  depends_on = [google_project_service.run_api]
}

resource "google_cloud_run_v2_job" "llm_worker" {
  name     = "gaper-llm-job"
  location = var.region

  template {
    template {
      service_account = google_service_account.cloud_run_sa.email
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.docker_repo_name}/worker:latest"
      }
    }
  }
  depends_on = [google_project_service.run_api]
}

# 7. Cloud Scheduler Triggers (Every 5 mins)
resource "google_cloud_scheduler_job" "trigger_router" {
  name             = "trigger-router-job"
  description      = "Trigger execution router job"
  schedule         = "*/5 * * * *"
  time_zone        = "Etc/UTC"
  attempt_deadline = "320s"
  region           = var.region

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/gaper-router-job:run"
    
    oauth_token {
      service_account_email = google_service_account.cloud_run_sa.email
    }
  }
  depends_on = [google_project_service.scheduler_api, google_cloud_run_v2_job.execution_router]
}

resource "google_cloud_scheduler_job" "trigger_llm" {
  name             = "trigger-llm-job"
  description      = "Trigger LLM job"
  schedule         = "*/5 * * * *"
  time_zone        = "Etc/UTC"
  attempt_deadline = "320s"
  region           = var.region

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/gaper-llm-job:run"
    
    oauth_token {
      service_account_email = google_service_account.cloud_run_sa.email
    }
  }
  depends_on = [google_project_service.scheduler_api, google_cloud_run_v2_job.llm_worker]
}
