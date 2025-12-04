# CloudWatch Dashboard for monitoring

resource "aws_cloudwatch_dashboard" "main" {
  count          = var.enable_cloudwatch_dashboard ? 1 : 0
  dashboard_name = "Graviton-Validator-${random_string.random.result}"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["AWS/Batch", "JobsSubmitted", "JobQueue", aws_batch_job_queue.main.name],
            [".", "JobsRunning", ".", "."],
            [".", "JobsSucceeded", ".", "."],
            [".", "JobsFailed", ".", "."]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "Batch Job Status (5min)"
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      {
        type   = "metric"
        x      = 8
        y      = 0
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["AWS/Batch", "RunningJobs", "JobQueue", aws_batch_job_queue.main.name, { stat = "Average", label = "Running Jobs" }],
            [".", "RunnableJobs", ".", ".", { stat = "Average", label = "Queued Jobs" }]
          ]
          period = 60
          stat   = "Average"
          region = var.aws_region
          title  = "Active Jobs (Real-time)"
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      {
        type   = "metric"
        x      = 16
        y      = 0
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", aws_lambda_function.batch_trigger.function_name],
            [".", "Errors", ".", "."],
            [".", "Duration", ".", ".", { stat = "Average" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "Lambda Metrics"
        }
      },
      {
        type   = "log"
        x      = 0
        y      = 6
        width  = 24
        height = 8
        properties = {
          query  = "SOURCE '${aws_cloudwatch_log_group.batch.name}' | fields @timestamp, @message | sort @timestamp desc | limit 50"
          region = var.aws_region
          title  = "Latest Job Logs (Last 50 entries)"
        }
      }
    ]
  })
}

# Optional: CloudWatch Alarm for Batch job failures
resource "aws_cloudwatch_metric_alarm" "batch_failures" {
  count               = var.enable_cloudwatch_dashboard ? 1 : 0
  alarm_name          = "graviton-validator-batch-failures-${random_string.random.result}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "JobsFailed"
  namespace           = "AWS/Batch"
  period              = 300
  statistic           = "Sum"
  threshold           = 3
  alarm_description   = "Alert when more than 3 Batch jobs fail"
  treat_missing_data  = "notBreaching"

  dimensions = {
    JobQueue = aws_batch_job_queue.main.name
  }

  tags = {
    Name = "graviton-validator-batch-failures-alarm"
  }
}
