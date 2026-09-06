output "environment_vpc_id" {
  description = "Terraform-managed environment VPC id when environment_network_enabled=true."
  value       = var.environment_network_enabled ? aws_vpc.environment[0].id : null
}

output "environment_public_subnet_ids" {
  description = "Terraform-managed public subnet ids."
  value       = local.environment_public_subnet_ids
}

output "environment_private_subnet_ids" {
  description = "Terraform-managed private subnet ids."
  value       = local.environment_private_subnet_ids
}

output "environment_nat_gateway_id" {
  description = "Single environment NAT gateway id when enabled."
  value       = var.environment_network_enabled && var.environment_single_nat_gateway_enabled ? aws_nat_gateway.environment[0].id : null
}

output "environment_s3_gateway_endpoint_id" {
  description = "S3 Gateway VPC endpoint id when enabled."
  value       = var.environment_network_enabled && var.environment_s3_gateway_endpoint_enabled ? aws_vpc_endpoint.s3_gateway[0].id : null
}

output "environment_route53_zone_id" {
  description = "Environment Route53 hosted-zone id when Terraform manages the environment zone."
  value       = var.environment_route53_zone_enabled ? aws_route53_zone.environment[0].zone_id : null
}

output "environment_route53_name_servers" {
  description = "Environment hosted-zone name servers. Delegate these from the parent verifyforgood.com hosted zone before ACM validation can complete."
  value       = var.environment_route53_zone_enabled ? aws_route53_zone.environment[0].name_servers : []
}

output "customer_documents_bucket_name" {
  description = "Private customer-document bucket name when enabled."
  value       = var.customer_documents_bucket_enabled ? aws_s3_bucket.customer_documents[0].bucket : null
}

output "github_deploy_role_arn" {
  description = "GitHub Actions OIDC deployment role ARN for this environment. Configure it as the GitHub Environment variable AWS_DEPLOY_ROLE_ARN after the one-time bootstrap apply."
  value       = var.github_oidc_deploy_role_enabled ? aws_iam_role.github_deploy[0].arn : null
}
