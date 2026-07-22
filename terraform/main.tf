provider "google" {
  project = var.project_id
  region  = var.region
}

# (APIs will be managed manually by project owner)

# 5. Dashboard (Cloud Run Service)
resource "google_cloud_run_v2_service" "dashboard" {
  name     = "abdul-dashboard"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false
  
  template {
    containers {
      image = "us-docker.pkg.dev/cloudrun/container/hello"
    }
  }

  lifecycle {
    ignore_changes = [
      template[0].containers[0].image
    ]
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
  name     = "abdul-router-job"
  location = var.region
  deletion_protection = false

  template {
    template {
      containers {
        image = "us-docker.pkg.dev/cloudrun/container/hello"
        resources {
          limits = {
            cpu    = "1"
            memory = "2Gi" # Playwright needs a bit more RAM
          }
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [
      template[0].template[0].containers[0].image
    ]
  }
}

resource "google_cloud_run_v2_job" "llm_worker" {
  name     = "abdul-llm-job"
  location = var.region
  deletion_protection = false

  template {
    template {
      containers {
        image = "us-docker.pkg.dev/cloudrun/container/hello"
      }
    }
  }

  lifecycle {
    ignore_changes = [
      template[0].template[0].containers[0].image
    ]
  }
}

# (Cloud Scheduler triggers removed. Jobs will be triggered via GitHub Actions CRON or manually to avoid GCP API limits)
