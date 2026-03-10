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
  value       = "s3://${var.source_data_bucket_name}/${local.source_data_prefix_normalized}"
}

output "athena_results_bucket_name" {
  description = "S3 bucket name used for Athena query results."
  value       = aws_s3_bucket.athena_results.bucket
}