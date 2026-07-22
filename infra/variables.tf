variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Short name used to prefix all created resources"
  type        = string
  default     = "multi-agent-report-gen"
}

variable "container_port" {
  description = "Port the app listens on inside the container"
  type        = number
  default     = 8000
}

variable "github_repo" {
  description = "GitHub repo allowed to assume the deploy role, as \"owner/repo\""
  type        = string
  default     = "MeghaUkkali9/Multi-Agent-Research-Analysis-Report-Generation-System"
}

variable "task_cpu" {
  description = "Fargate task vCPU units (256 = 0.25 vCPU)"
  type        = string
  default     = "256"
}

variable "task_memory" {
  description = "Fargate task memory in MB"
  type        = string
  default     = "512"
}
