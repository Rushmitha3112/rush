resource "aws_iam_role" "redshift_copy" {
  name = "${local.name}-redshift-copy"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "sts:AssumeRole", Principal = { Service = "redshift.amazonaws.com" } }]
  })
}

resource "aws_iam_role_policy" "redshift_copy" {
  role = aws_iam_role.redshift_copy.id
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = ["s3:GetObject", "s3:ListBucket"], Resource = [aws_s3_bucket.curated.arn, "${aws_s3_bucket.curated.arn}/*"] }]
  })
}

resource "aws_redshiftserverless_namespace" "wh" {
  namespace_name        = local.name
  db_name               = "dev"
  iam_roles             = [aws_iam_role.redshift_copy.arn]
  manage_admin_password = true
}

resource "aws_redshiftserverless_workgroup" "wh" {
  namespace_name = aws_redshiftserverless_namespace.wh.namespace_name
  workgroup_name = local.name
  base_capacity  = var.redshift_base_rpu
  # billed per RPU-second only while queries run; the daily load is a few minutes
}
