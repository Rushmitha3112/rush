output "raw_bucket" { value = aws_s3_bucket.raw.bucket }
output "curated_bucket" { value = aws_s3_bucket.curated.bucket }
output "glue_job" { value = aws_glue_job.transform.name }
output "redshift_workgroup" { value = aws_redshiftserverless_workgroup.wh.workgroup_name }
