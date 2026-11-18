resource "aws_s3_object" "glue_script" {
  bucket = aws_s3_bucket.artifacts.id
  key    = "glue/job.py"
  source = "../../glue/job.py"
  etag   = filemd5("../../glue/job.py")
}

resource "aws_s3_object" "glue_lib" {
  bucket = aws_s3_bucket.artifacts.id
  key    = "glue/lastmile.zip"
  source = "${var.build_dir}/lastmile.zip"
  etag   = filemd5("${var.build_dir}/lastmile.zip")
}

resource "aws_iam_role" "glue" {
  name = "${local.name}-glue"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "sts:AssumeRole", Principal = { Service = "glue.amazonaws.com" } }]
  })
}

resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.glue.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy" "glue_data" {
  role = aws_iam_role.glue.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["s3:GetObject", "s3:ListBucket"], Resource = [aws_s3_bucket.raw.arn, "${aws_s3_bucket.raw.arn}/*", aws_s3_bucket.artifacts.arn, "${aws_s3_bucket.artifacts.arn}/*"] },
      { Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"], Resource = [aws_s3_bucket.curated.arn, "${aws_s3_bucket.curated.arn}/*"] },
    ]
  })
}

resource "aws_glue_job" "transform" {
  name              = "${local.name}-transform"
  role_arn          = aws_iam_role.glue.arn
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = var.glue_workers
  timeout           = 30 # minutes. a normal day takes a few, so 30 means something is wrong

  command {
    name            = "glueetl"
    python_version  = "3"
    script_location = "s3://${aws_s3_bucket.artifacts.bucket}/${aws_s3_object.glue_script.key}"
  }

  execution_property {
    max_concurrent_runs = 4 # lets a backfill run a few days in parallel; each run owns its own partition
  }

  default_arguments = {
    "--extra-py-files"                   = "s3://${aws_s3_bucket.artifacts.bucket}/${aws_s3_object.glue_lib.key}"
    "--raw_root"                         = "s3://${aws_s3_bucket.raw.bucket}"
    "--curated_root"                     = "s3://${aws_s3_bucket.curated.bucket}"
    "--enable-metrics"                   = "true"
    "--enable-continuous-cloudwatch-log" = "true"
    "--conf"                             = "spark.sql.sources.partitionOverwriteMode=dynamic"
  }
}
