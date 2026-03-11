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
