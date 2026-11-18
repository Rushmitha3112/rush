data "archive_file" "lambda" {
  type        = "zip"
  source_dir  = "${var.build_dir}/lambda"
  output_path = "${var.build_dir}/lambda.zip"
}

resource "aws_iam_role" "lambda" {
  name = "${local.name}-lambda"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "sts:AssumeRole", Principal = { Service = "lambda.amazonaws.com" } }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda" {
  role = aws_iam_role.lambda.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["s3:GetObject", "s3:ListBucket"], Resource = [aws_s3_bucket.raw.arn, "${aws_s3_bucket.raw.arn}/*"] },
      { Effect = "Allow", Action = ["glue:StartJobRun", "glue:GetJobRun"], Resource = aws_glue_job.transform.arn },
      { Effect = "Allow", Action = "sns:Publish", Resource = aws_sns_topic.alerts.arn },
      { Effect = "Allow", Action = ["redshift-data:BatchExecuteStatement", "redshift-data:DescribeStatement"], Resource = "*" },
      { Effect = "Allow", Action = "redshift-serverless:GetCredentials", Resource = aws_redshiftserverless_workgroup.wh.arn },
    ]
  })
}

# fires on every manifest, validates the drop and starts Glue
resource "aws_lambda_function" "trigger" {
  function_name    = "${local.name}-trigger"
  role             = aws_iam_role.lambda.arn
  runtime          = "python3.11"
  handler          = "lastmile.handler.lambda_handler"
  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256
  timeout          = 60
  environment {
    variables = {
      GLUE_JOB_NAME   = aws_glue_job.transform.name
      ALERT_TOPIC_ARN = aws_sns_topic.alerts.arn
      RAW_BUCKET      = aws_s3_bucket.raw.bucket
      CURATED_BUCKET  = aws_s3_bucket.curated.bucket
    }
  }
}

resource "aws_lambda_permission" "s3" {
  statement_id  = "s3-manifest"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.trigger.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.raw.arn
}

resource "aws_s3_bucket_notification" "manifest" {
  bucket = aws_s3_bucket.raw.id
  lambda_function {
    lambda_function_arn = aws_lambda_function.trigger.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "almrrc/"
    filter_suffix       = "_manifest.json"
  }
  depends_on = [aws_lambda_permission.s3]
}

# runs after a successful Glue run and loads that date into Redshift
resource "aws_lambda_function" "loader" {
  function_name    = "${local.name}-loader"
  role             = aws_iam_role.lambda.arn
  runtime          = "python3.11"
  handler          = "lastmile.redshift_loader.lambda_handler"
  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256
  timeout          = 300
  environment {
    variables = {
      CURATED_BUCKET     = aws_s3_bucket.curated.bucket
      REDSHIFT_WORKGROUP = aws_redshiftserverless_workgroup.wh.workgroup_name
      REDSHIFT_COPY_ROLE = aws_iam_role.redshift_copy.arn
    }
  }
}
