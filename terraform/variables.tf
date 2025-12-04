variable "aws_region" {
  type        = string
  description = "AWS region for deployment"
  default     = "us-east-1"
}

variable "bucket_name" {
  type        = string
  description = "S3 bucket name prefix for SBOM files and results"
  default     = "graviton-validator"
}

# VPC Configuration
variable "create_vpc" {
  type        = bool
  description = "Create new VPC or use existing"
  default     = true
}

variable "existing_vpc_id" {
  type        = string
  description = "Existing VPC ID (required if create_vpc=false)"
  default     = ""
}

variable "existing_public_subnet_ids" {
  type        = list(string)
  description = "Existing public subnet IDs (required if create_vpc=false)"
  default     = []
}

variable "existing_private_subnet_ids" {
  type        = list(string)
  description = "Existing private subnet IDs (optional)"
  default     = []
}

# AWS Batch Configuration
variable "batch_instance_type" {
  type        = string
  description = "EC2 instance type for Batch compute environment"
  default     = "m7g.xlarge"
}

variable "batch_max_vcpus" {
  type        = number
  description = "Maximum vCPUs for Batch compute environment (max instances = max_vcpus / instance_vcpus)"
  default     = 20
}

# CloudWatch Logs Configuration
variable "log_retention_days" {
  type        = number
  description = "CloudWatch log retention in days (30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653)"
  default     = 365

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.log_retention_days)
    error_message = "Log retention must be one of: 1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653 days."
  }
}

variable "batch_use_spot" {
  type        = bool
  description = "Use Spot instances for up to 90% cost savings"
  default     = false
}

variable "batch_spot_instance_types" {
  type        = list(string)
  description = "List of Graviton instance types for Spot (better availability with multiple types)"
  default     = ["m7g.xlarge", "m7g.large", "m6g.xlarge", "m6g.large", "c7g.xlarge"]
}

variable "batch_job_vcpus" {
  type        = number
  description = "vCPUs allocated per Batch job"
  default     = 3
}

variable "batch_job_memory" {
  type        = number
  description = "Memory (MB) allocated per Batch job"
  default     = 15360
}

# Monitoring
variable "enable_cloudwatch_dashboard" {
  type        = bool
  description = "Enable CloudWatch dashboard for monitoring"
  default     = true
}
