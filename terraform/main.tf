provider "google" {
  project = var.project_id
  region  = var.region
}

# (APIs will be managed manually by project owner)

# 2. Artifact Registry for Docker Images
resource "google_artifact_registry_repository" "repo" {
  provider      = google
  location      = var.region
  repository_id = var.docker_repo_name
  description   = "Docker repository for Gaper Backlink Engine"
  format        = "DOCKER"
}

# (Bucket and Service Account removed for Redis-based architecture)

# 5. Dashboard (Cloud Run Service)
resource "google_cloud_run_v2_service" "dashboard" {
  name     = "gaper-dashboard"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"
  
  template {
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.docker_repo_name}/dashboard:latest"
    }
  }
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
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.docker_repo_name}/router:latest"
        resources {
          limits = {
            cpu    = "1"
            memory = "2Gi" # Playwright needs a bit more RAM
          }
        }
      }
    }
  }
}

resource "google_cloud_run_v2_job" "llm_worker" {
  name     = "gaper-llm-job"
  location = var.region

  template {
    template {
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.docker_repo_name}/worker:latest"
      }
    }
  }
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
  }
  depends_on = [google_cloud_run_v2_job.execution_router]
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
  }
  depends_on = [google_cloud_run_v2_job.llm_worker]
}
