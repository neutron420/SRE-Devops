output "eks_cluster_name" {
  description = "EKS Cluster Name"
  value       = aws_eks_cluster.main.name
}

output "eks_endpoint" {
  description = "Endpoint for EKS control plane"
  value       = aws_eks_cluster.main.endpoint
}

output "ecr_backend_url" {
  description = "ECR Repository URL for Backend"
  value       = aws_ecr_repository.backend.repository_url
}

output "ecr_bot_url" {
  description = "ECR Repository URL for Discord Bot"
  value       = aws_ecr_repository.bot.repository_url
}

output "aws_region" {
  description = "AWS Region"
  value       = var.aws_region
}
