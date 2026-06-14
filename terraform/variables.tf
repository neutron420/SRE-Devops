variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Name prefix for all resources"
  type        = string
  default     = "sre-copilot"
}

variable "instance_type" {
  description = "EC2 instance type (t3.small = 2 vCPU, 2GB RAM)"
  type        = string
  default     = "t3.small"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
}
