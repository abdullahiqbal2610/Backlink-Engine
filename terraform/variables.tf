variable "project_id" {
  description = "The GCP Project ID"
  type        = string
  default     = "backlink-engine-deployment"
}

variable "region" {
  description = "The GCP region to deploy to"
  type        = string
  default     = "us-central1"
}

variable "docker_repo_name" {
  description = "The name of the Artifact Registry repository"
  type        = string
  default     = "backlink-engine-repo"
}

variable "cookie_bucket_name" {
  description = "The name of the GCS bucket to store browser cookies"
  type        = string
  default     = "backlink-engine-cookies-bucket-2026"
}
