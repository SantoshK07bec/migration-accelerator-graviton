# EventBridge Rules for S3 upload detection

# Individual SBOM Rule
resource "aws_cloudwatch_event_rule" "individual" {
  name        = "graviton-validator-individual-${random_string.random.result}"
  description = "Trigger Lambda for individual SBOM uploads"

  event_pattern = jsonencode({
    source      = ["aws.s3"]
    detail-type = ["Object Created"]
    detail = {
      bucket = {
        name = [aws_s3_bucket.main.id]
      }
      object = {
        key = [
          { prefix = "input/individual/" },
          { suffix = ".json" }
        ]
      }
    }
  })

  tags = {
    Name = "graviton-validator-individual-rule"
  }
}

resource "aws_cloudwatch_event_target" "individual" {
  rule      = aws_cloudwatch_event_rule.individual.name
  target_id = "TriggerLambdaIndividual"
  arn       = aws_lambda_function.batch_trigger.arn
}

# Batch SBOM Rule (only triggers on batch-manifest.txt)
resource "aws_cloudwatch_event_rule" "batch" {
  name        = "graviton-validator-batch-${random_string.random.result}"
  description = "Trigger Lambda for batch manifest uploads"

  event_pattern = jsonencode({
    source      = ["aws.s3"]
    detail-type = ["Object Created"]
    detail = {
      bucket = {
        name = [aws_s3_bucket.main.id]
      }
      object = {
        key = [
          { suffix = "batch-manifest.txt" }
        ]
      }
    }
  })

  tags = {
    Name = "graviton-validator-batch-rule"
  }
}

resource "aws_cloudwatch_event_target" "batch" {
  rule      = aws_cloudwatch_event_rule.batch.name
  target_id = "TriggerLambdaBatch"
  arn       = aws_lambda_function.batch_trigger.arn
}

# Lambda permissions for EventBridge
resource "aws_lambda_permission" "eventbridge_individual" {
  statement_id  = "AllowExecutionFromEventBridgeIndividual"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.batch_trigger.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.individual.arn
}

resource "aws_lambda_permission" "eventbridge_batch" {
  statement_id  = "AllowExecutionFromEventBridgeBatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.batch_trigger.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.batch.arn
}
