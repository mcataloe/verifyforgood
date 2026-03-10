output "athena_workgroup_name" {
  description = "Athena workgroup name for EO BMF queries."
  value       = aws_athena_workgroup.irs.name
}

output "glue_database_name" {
  description = "Glue Data Catalog database name for IRS EO BMF tables."
  value       = aws_glue_catalog_database.irs.name
}

output "glue_table_names" {
  description = "Glue table names keyed by IRS EO BMF file type."
  value = {
    eo1   = aws_glue_catalog_table.eo1.name
    eo2   = aws_glue_catalog_table.eo2.name
    eo3   = aws_glue_catalog_table.eo3.name
    eo4   = aws_glue_catalog_table.eo4.name
    eo_pr = aws_glue_catalog_table.eo_pr.name
    eo_xx = aws_glue_catalog_table.eo_xx.name
  }
}

output "athena_results_bucket_name" {
  description = "S3 bucket name used for Athena query results."
  value       = aws_s3_bucket.athena_results.bucket
}