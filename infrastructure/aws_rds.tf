#############################################
# PLATFORM POSTGRESQL FOUNDATION
#############################################

locals {
  platform_postgres_backup_retention_days_effective = var.platform_postgres_backup_retention_days != null ? var.platform_postgres_backup_retention_days : (local.environment_slug == "prod" ? 7 : 1)
  platform_postgres_deletion_protection_effective   = var.platform_postgres_deletion_protection_enabled != null ? var.platform_postgres_deletion_protection_enabled : local.environment_slug == "prod"
  platform_postgres_skip_final_snapshot_effective   = var.platform_postgres_skip_final_snapshot != null ? var.platform_postgres_skip_final_snapshot : local.environment_slug != "prod"
  platform_postgres_secret_arn_resolved             = !var.platform_postgres_enabled ? "" : (trim(var.platform_postgres_existing_secret_arn, " ") != "" ? trim(var.platform_postgres_existing_secret_arn, " ") : aws_secretsmanager_secret.platform_postgres[0].arn)
  platform_postgres_username_resolved               = !var.platform_postgres_enabled ? "" : (trim(var.platform_postgres_existing_secret_arn, " ") != "" ? try(jsondecode(data.aws_secretsmanager_secret_version.platform_postgres_existing[0].secret_string).username, var.platform_postgres_username) : var.platform_postgres_username)
  platform_postgres_password_resolved               = !var.platform_postgres_enabled ? "" : (trim(var.platform_postgres_existing_secret_arn, " ") != "" ? tostring(try(jsondecode(data.aws_secretsmanager_secret_version.platform_postgres_existing[0].secret_string).password, "")) : random_password.platform_postgres[0].result)
}

resource "random_password" "platform_postgres" {
  count   = var.platform_postgres_enabled && trim(var.platform_postgres_existing_secret_arn, " ") == "" ? 1 : 0
  length  = 32
  special = true
}

data "aws_secretsmanager_secret_version" "platform_postgres_existing" {
  count     = var.platform_postgres_enabled && trim(var.platform_postgres_existing_secret_arn, " ") != "" ? 1 : 0
  secret_id = trim(var.platform_postgres_existing_secret_arn, " ")
}

resource "aws_secretsmanager_secret" "platform_postgres" {
  count                   = var.platform_postgres_enabled && trim(var.platform_postgres_existing_secret_arn, " ") == "" ? 1 : 0
  name                    = local.platform_postgres_secret_name
  recovery_window_in_days = local.environment_slug == "prod" ? 30 : 7
  kms_key_id              = trim(var.platform_postgres_secret_kms_key_arn, " ") != "" ? trim(var.platform_postgres_secret_kms_key_arn, " ") : null
  tags                    = local.platform_common_tags
}

resource "aws_db_subnet_group" "platform_postgres" {
  count       = var.platform_postgres_enabled ? 1 : 0
  name        = local.platform_postgres_subnet_group_name
  subnet_ids  = var.platform_postgres_private_subnet_ids
  description = "Private subnet group for the platform PostgreSQL RDS instance."
  tags        = local.platform_common_tags
}

resource "aws_security_group" "query_lambda_postgres" {
  count       = var.platform_postgres_enabled ? 1 : 0
  name        = local.query_lambda_postgres_sg_name
  description = "Security group attached to the query Lambda for PostgreSQL access."
  vpc_id      = var.platform_postgres_vpc_id
  tags        = local.platform_common_tags
}

resource "aws_security_group" "platform_postgres" {
  count       = var.platform_postgres_enabled ? 1 : 0
  name        = local.platform_postgres_security_group_name
  description = "Security group for the platform PostgreSQL RDS instance."
  vpc_id      = var.platform_postgres_vpc_id

  ingress {
    description = "Allow PostgreSQL access from the query Lambda and ECS API tasks."
    from_port   = var.platform_postgres_port
    to_port     = var.platform_postgres_port
    protocol    = "tcp"
    security_groups = concat(
      [aws_security_group.query_lambda_postgres[0].id],
      var.api_ecs_enabled ? [aws_security_group.api_task[0].id] : [],
    )
  }

  tags = local.platform_common_tags
}

resource "aws_db_instance" "platform_postgres" {
  count                      = var.platform_postgres_enabled ? 1 : 0
  identifier                 = local.platform_postgres_instance_name
  engine                     = "postgres"
  engine_version             = trim(var.platform_postgres_engine_version, " ") != "" ? trim(var.platform_postgres_engine_version, " ") : null
  instance_class             = var.platform_postgres_instance_class
  allocated_storage          = var.platform_postgres_allocated_storage_gib
  max_allocated_storage      = var.platform_postgres_max_allocated_storage_gib
  db_name                    = var.platform_postgres_database_name
  username                   = local.platform_postgres_username_resolved
  password                   = local.platform_postgres_password_resolved
  port                       = var.platform_postgres_port
  db_subnet_group_name       = aws_db_subnet_group.platform_postgres[0].name
  vpc_security_group_ids     = [aws_security_group.platform_postgres[0].id]
  backup_retention_period    = local.platform_postgres_backup_retention_days_effective
  publicly_accessible        = var.platform_postgres_publicly_accessible
  storage_encrypted          = true
  multi_az                   = false
  deletion_protection        = local.platform_postgres_deletion_protection_effective
  skip_final_snapshot        = local.platform_postgres_skip_final_snapshot_effective
  final_snapshot_identifier  = local.platform_postgres_skip_final_snapshot_effective ? null : "${local.platform_postgres_instance_name}-final"
  apply_immediately          = local.environment_slug != "prod"
  auto_minor_version_upgrade = true
  backup_window              = local.environment_slug == "prod" ? "04:00-05:00" : null
  maintenance_window         = local.environment_slug == "prod" ? "sun:05:00-sun:06:00" : null
  copy_tags_to_snapshot      = true

  tags = local.platform_common_tags
}

resource "aws_secretsmanager_secret_version" "platform_postgres_managed" {
  count     = var.platform_postgres_enabled && trim(var.platform_postgres_existing_secret_arn, " ") == "" ? 1 : 0
  secret_id = aws_secretsmanager_secret.platform_postgres[0].id
  secret_string = jsonencode({
    engine   = "postgres"
    host     = aws_db_instance.platform_postgres[0].address
    port     = aws_db_instance.platform_postgres[0].port
    database = var.platform_postgres_database_name
    username = local.platform_postgres_username_resolved
    password = local.platform_postgres_password_resolved
    sslmode  = var.platform_postgres_sslmode
    url      = "postgresql://${local.platform_postgres_username_resolved}:${local.platform_postgres_password_resolved}@${aws_db_instance.platform_postgres[0].address}:${aws_db_instance.platform_postgres[0].port}/${var.platform_postgres_database_name}"
  })
}
