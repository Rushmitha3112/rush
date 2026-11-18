resource "aws_sns_topic" "alerts" {
  name = "${local.name}-alerts"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_sns_topic_policy" "events" {
  arn = aws_sns_topic.alerts.arn
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "events.amazonaws.com" }, Action = "sns:Publish", Resource = aws_sns_topic.alerts.arn }]
  })
}

# Glue run failed / timed out -> email
resource "aws_cloudwatch_event_rule" "glue_failed" {
  name = "${local.name}-glue-failed"
  event_pattern = jsonencode({
    source        = ["aws.glue"]
    "detail-type" = ["Glue Job State Change"]
    detail        = { jobName = [aws_glue_job.transform.name], state = ["FAILED", "TIMEOUT", "ERROR"] }
  })
}

resource "aws_cloudwatch_event_target" "glue_failed" {
  rule = aws_cloudwatch_event_rule.glue_failed.name
  arn  = aws_sns_topic.alerts.arn
}

# Glue run succeeded -> load into Redshift
resource "aws_cloudwatch_event_rule" "glue_ok" {
  name = "${local.name}-glue-succeeded"
  event_pattern = jsonencode({
    source        = ["aws.glue"]
    "detail-type" = ["Glue Job State Change"]
    detail        = { jobName = [aws_glue_job.transform.name], state = ["SUCCEEDED"] }
  })
}

resource "aws_cloudwatch_event_target" "glue_ok" {
  rule = aws_cloudwatch_event_rule.glue_ok.name
  arn  = aws_lambda_function.loader.arn
}

resource "aws_lambda_permission" "events_loader" {
  statement_id  = "eventbridge-glue-ok"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.loader.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.glue_ok.arn
}

# either Lambda erroring (rejected drop, failed load) -> email
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  for_each            = { trigger = aws_lambda_function.trigger.function_name, loader = aws_lambda_function.loader.function_name }
  alarm_name          = "${each.value}-errors"
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  dimensions          = { FunctionName = each.value }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}
