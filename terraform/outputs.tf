output "ec2_public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = aws_eip.copilot.public_ip
}

output "ssh_command" {
  description = "SSH command to connect to the instance"
  value       = "ssh -i terraform/${var.project_name}-key.pem ec2-user@${aws_eip.copilot.public_ip}"
}

output "api_url" {
  description = "FastAPI Backend URL"
  value       = "http://${aws_eip.copilot.public_ip}:8000"
}

output "api_docs_url" {
  description = "FastAPI Interactive Docs"
  value       = "http://${aws_eip.copilot.public_ip}:8000/docs"
}

output "grafana_url" {
  description = "Grafana Dashboard URL"
  value       = "http://${aws_eip.copilot.public_ip}:3000"
}

output "prometheus_url" {
  description = "Prometheus URL"
  value       = "http://${aws_eip.copilot.public_ip}:9090"
}

output "aws_region" {
  description = "AWS Region"
  value       = var.aws_region
}

output "ssh_key_path" {
  description = "Path to the SSH private key"
  value       = local_file.ssh_key.filename
}
