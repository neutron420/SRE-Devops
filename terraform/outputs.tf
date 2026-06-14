output "eks_cluster_name" {
  description = "EKS Cluster Name"
  value       = aws_eks_cluster.main.name
}

output "eks_endpoint" {
  description = "Endpoint for EKS control plane"
  value       = aws_eks_cluster.main.endpoint
}

output "aws_region" {
  description = "AWS Region"
  value       = var.aws_region
}
