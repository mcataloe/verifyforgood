output "athena_workgroup_name" {
  description = "Athena workgroup name for EO BMF queries."
  value       = aws_athena_workgroup.eo_bmf.name
}

output "glue_database_name" {
  description = "Glue Data Catalog database name for IRS EO BMF table."
  value       = aws_glue_catalog_database.eo_bmf.name
}

output "glue_table_name" {
  description = "Glue table name for IRS EO BMF dataset."
  value       = aws_glue_catalog_table.eo_bmf.name
}

output "source_s3_location" {
  description = "S3 location backing the EO BMF Glue table."
  value       = "s3://${local.source_data_bucket_name}/${local.source_data_prefix_normalized}"
}

output "athena_results_bucket_name" {
  description = "S3 bucket name used for Athena query results."
  value       = aws_s3_bucket.athena_results.bucket
}

output "form990_metadata_glue_table_name" {
  description = "Glue table name for normalized Form 990 metadata."
  value       = aws_glue_catalog_table.form990_metadata.name
}

output "form990_raw_s3_prefix" {
  description = "S3 prefix for raw Form 990 XML documents."
  value       = local.form990_raw_prefix_normalized
}

output "form990_raw_source_s3_prefix" {
  description = "S3 prefix for raw IRS Form 990 source artifacts (original CSV and ZIP files)."
  value       = local.form990_raw_source_prefix_normalized
}

output "form990_metadata_s3_prefix" {
  description = "S3 prefix for normalized Form 990 metadata JSONL."
  value       = local.form990_metadata_prefix_normalized
}

output "form990_metrics_glue_table_name" {
  description = "Glue table name for Form 990 derived metrics."
  value       = aws_glue_catalog_table.form990_metrics.name
}

output "form990_governance_glue_table_name" {
  description = "Glue table name for Form 990 governance indicators."
  value       = aws_glue_catalog_table.form990_governance.name
}

output "form990_quality_glue_table_name" {
  description = "Glue table name for Form 990 filing quality indicators."
  value       = aws_glue_catalog_table.form990_quality.name
}

output "profiles_dynamodb_table_name" {
  description = "DynamoDB table for materialized nonprofit serving profiles."
  value       = aws_dynamodb_table.profiles.name
}

output "identity_dynamodb_table_name" {
  description = "DynamoDB table for identity, organizations, memberships, invitations, and audit records."
  value       = aws_dynamodb_table.identity.name
}

output "organization_settings_dynamodb_table_name" {
  description = "DynamoDB table for organization-level integration settings."
  value       = aws_dynamodb_table.organization_settings.name
}

output "control_plane_dynamodb_table_name" {
  description = "DynamoDB table for control-plane accounts, subscriptions, managed credentials, and usage."
  value       = aws_dynamodb_table.control_plane.name
}

output "platform_postgres_endpoint" {
  description = "Endpoint address for the platform PostgreSQL RDS instance."
  value       = var.platform_postgres_enabled ? aws_db_instance.platform_postgres[0].address : null
}

output "platform_postgres_port" {
  description = "Port for the platform PostgreSQL RDS instance."
  value       = var.platform_postgres_enabled ? aws_db_instance.platform_postgres[0].port : null
}

output "platform_postgres_database_name" {
  description = "Database name for the platform PostgreSQL RDS instance."
  value       = var.platform_postgres_enabled ? aws_db_instance.platform_postgres[0].db_name : null
}

output "platform_postgres_secret_arn" {
  description = "Secrets Manager ARN used for platform PostgreSQL credentials."
  value       = var.platform_postgres_enabled ? local.platform_postgres_secret_arn_resolved : null
}

output "platform_postgres_subnet_group_name" {
  description = "Subnet group name for the platform PostgreSQL RDS instance."
  value       = var.platform_postgres_enabled ? aws_db_subnet_group.platform_postgres[0].name : null
}

output "platform_postgres_security_group_id" {
  description = "Security group id attached to the platform PostgreSQL RDS instance."
  value       = var.platform_postgres_enabled ? aws_security_group.platform_postgres[0].id : null
}

output "api_ecs_cluster_name" {
  description = "ECS cluster name for the parallel API service."
  value       = var.api_ecs_enabled ? aws_ecs_cluster.api[0].name : null
}

output "api_ecs_cluster_arn" {
  description = "ECS cluster ARN for the parallel API service."
  value       = var.api_ecs_enabled ? aws_ecs_cluster.api[0].arn : null
}

output "api_ecr_repository_url" {
  description = "ECR repository URL for the managed API service image."
  value       = var.api_ecs_enabled ? aws_ecr_repository.api[0].repository_url : null
}

output "api_ecs_service_name" {
  description = "ECS service name for the parallel API runtime."
  value       = var.api_ecs_enabled ? aws_ecs_service.api[0].name : null
}

output "api_ecs_task_definition_arn" {
  description = "ECS task definition ARN for the parallel API runtime."
  value       = var.api_ecs_enabled ? aws_ecs_task_definition.api[0].arn : null
}

output "api_ecs_task_log_group_name" {
  description = "CloudWatch log group used by the parallel ECS API service."
  value       = var.api_ecs_enabled ? aws_cloudwatch_log_group.api_task[0].name : null
}

output "api_alb_dns_name" {
  description = "DNS name of the parallel API application load balancer."
  value       = var.api_ecs_enabled ? aws_lb.api[0].dns_name : null
}

output "api_alb_zone_id" {
  description = "Route53 zone id for the parallel API application load balancer alias target."
  value       = var.api_ecs_enabled ? aws_lb.api[0].zone_id : null
}

output "api_alb_target_group_arn" {
  description = "Target group ARN for the parallel ECS API service."
  value       = var.api_ecs_enabled ? aws_lb_target_group.api[0].arn : null
}

output "backend_runtime_ecs_cluster_name" {
  description = "Shared ECS cluster name for backend API and worker services."
  value       = (var.api_ecs_enabled || var.worker_ecs_enabled) ? aws_ecs_cluster.api[0].name : null
}

output "backend_runtime_ecs_cluster_arn" {
  description = "Shared ECS cluster ARN for backend API and worker services."
  value       = (var.api_ecs_enabled || var.worker_ecs_enabled) ? aws_ecs_cluster.api[0].arn : null
}

output "worker_ecr_repository_url" {
  description = "ECR repository URL for the managed worker service image."
  value       = var.worker_ecs_enabled && trim(var.worker_ecs_image_uri, " ") == "" ? aws_ecr_repository.worker[0].repository_url : null
}

output "worker_ecs_service_name" {
  description = "ECS service name for the backend worker runtime placeholder."
  value       = var.worker_ecs_enabled ? aws_ecs_service.worker[0].name : null
}

output "worker_ecs_task_definition_arn" {
  description = "ECS task definition ARN for the backend worker runtime placeholder."
  value       = var.worker_ecs_enabled ? aws_ecs_task_definition.worker[0].arn : null
}

output "worker_ecs_task_log_group_name" {
  description = "CloudWatch log group used by the backend worker ECS service."
  value       = var.worker_ecs_enabled ? aws_cloudwatch_log_group.worker_task[0].name : null
}

output "monthly_ingest_state_machine_name" {
  description = "Step Functions state machine name for the monthly private-ingest workflow."
  value       = var.monthly_ingest_state_machine_enabled ? aws_sfn_state_machine.monthly_ingest[0].name : null
}

output "monthly_ingest_state_machine_arn" {
  description = "Step Functions state machine ARN for the monthly private-ingest workflow."
  value       = var.monthly_ingest_state_machine_enabled ? aws_sfn_state_machine.monthly_ingest[0].arn : null
}

output "monthly_ingest_worker_ecr_repository_url" {
  description = "ECR repository URL for the managed monthly private-ingest ECS worker image."
  value       = local.monthly_ingest_managed_task_definition_enabled ? aws_ecr_repository.monthly_ingest_worker[0].repository_url : null
}

output "monthly_ingest_task_definition_arn" {
  description = "ECS task definition ARN used by the monthly private-ingest workflow."
  value       = trim(local.monthly_ingest_task_definition_arn_resolved, " ") != "" ? local.monthly_ingest_task_definition_arn_resolved : null
}

output "monthly_ingest_ecs_task_log_group_name" {
  description = "CloudWatch log group used by the monthly private-ingest ECS worker."
  value       = local.monthly_ingest_managed_task_definition_enabled ? aws_cloudwatch_log_group.monthly_ingest_task[0].name : null
}

output "monthly_ingest_staging_lambda_arn" {
  description = "Lambda ARN used to stage the monthly vendor ZIP before ECS processing."
  value       = local.monthly_ingest_staging_lambda_configured ? local.monthly_ingest_staging_lambda_arn_resolved : null
}

output "monthly_ingest_step_function_log_group_name" {
  description = "CloudWatch log group used by the monthly private-ingest Step Functions workflow."
  value       = var.monthly_ingest_state_machine_enabled ? aws_cloudwatch_log_group.monthly_ingest_state_machine[0].name : null
}
