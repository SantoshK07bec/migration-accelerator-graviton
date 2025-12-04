# Outputs

# S3
output "s3_bucket_name" {
  description = "Name of the S3 bucket for SBOM files and results"
  value       = aws_s3_bucket.main.id
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.main.arn
}

# VPC
output "vpc_id" {
  description = "VPC ID (created or existing)"
  value       = local.vpc_id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = local.public_subnet_ids
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = local.private_subnet_ids
}

# AWS Batch
output "batch_compute_environment_arn" {
  description = "ARN of the Batch compute environment"
  value       = aws_batch_compute_environment.main.arn
}

output "batch_job_queue_name" {
  description = "Name of the Batch job queue"
  value       = aws_batch_job_queue.main.name
}

output "batch_job_queue_arn" {
  description = "ARN of the Batch job queue"
  value       = aws_batch_job_queue.main.arn
}

output "batch_job_definition_name" {
  description = "Name of the Batch job definition"
  value       = aws_batch_job_definition.main.name
}

output "batch_job_definition_arn" {
  description = "ARN of the Batch job definition"
  value       = aws_batch_job_definition.main.arn
}

# Lambda
output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.batch_trigger.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.batch_trigger.arn
}

# Monitoring
output "cloudwatch_log_group_batch" {
  description = "CloudWatch log group for Batch jobs"
  value       = aws_cloudwatch_log_group.batch.name
}

output "cloudwatch_log_group_lambda" {
  description = "CloudWatch log group for Lambda function"
  value       = aws_cloudwatch_log_group.lambda.name
}

output "dashboard_url" {
  description = "CloudWatch dashboard URL"
  value       = var.enable_cloudwatch_dashboard ? "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.main[0].dashboard_name}" : "Dashboard not enabled"
}

# Usage Instructions
output "usage_instructions" {
  description = "Instructions for using the Graviton Validator"
  value       = <<-EOT
    
    ╔═══════════════════════════════════════════════════════════════════════╗
    ║          GRAVITON VALIDATOR - AWS BATCH DEPLOYMENT                    ║
    ╚═══════════════════════════════════════════════════════════════════════╝
    
    📦 S3 Bucket: ${aws_s3_bucket.main.id}
    🔧 Batch Queue: ${aws_batch_job_queue.main.name}
    📊 Dashboard: https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${var.enable_cloudwatch_dashboard ? aws_cloudwatch_dashboard.main[0].dashboard_name : "not-enabled"}
    
    ⚠️  CRITICAL: Enable S3 EventBridge notifications (required):
    
    aws s3api put-bucket-notification-configuration \
      --bucket ${aws_s3_bucket.main.id} \
      --notification-configuration '{"EventBridgeConfiguration": {}}'
    
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    📝 INDIVIDUAL MODE (One SBOM at a time):
    
    aws s3 cp my-app.sbom.json s3://${aws_s3_bucket.main.id}/input/individual/
    
    ✅ Automatically triggers Batch job
    ✅ Results: s3://${aws_s3_bucket.main.id}/output/individual/my-app/
    
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    📝 BATCH MODE (Multiple SBOMs per project):
    
    # Step 1: Upload SBOMs (no trigger)
    aws s3 cp app1.sbom.json s3://${aws_s3_bucket.main.id}/input/batch/my-project/
    aws s3 cp app2.sbom.json s3://${aws_s3_bucket.main.id}/input/batch/my-project/
    aws s3 cp app3.sbom.json s3://${aws_s3_bucket.main.id}/input/batch/my-project/
    
    # Step 2: Create manifest
    cat > batch-manifest.txt <<EOF
    # My Project Analysis
    app1.sbom.json
    app2.sbom.json
    app3.sbom.json
    EOF
    
    # Step 3: Upload manifest (triggers ONE job)
    aws s3 cp batch-manifest.txt s3://${aws_s3_bucket.main.id}/input/batch/my-project/
    
    ✅ Triggers single Batch job for entire project
    ✅ Results: s3://${aws_s3_bucket.main.id}/output/batch/my-project/
    
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    🔍 MONITORING:
    
    # Check Batch jobs
    aws batch list-jobs --job-queue ${aws_batch_job_queue.main.name} --job-status RUNNING
    
    # View logs
    aws logs tail ${aws_cloudwatch_log_group.batch.name} --follow
    
    # Check results
    aws s3 ls s3://${aws_s3_bucket.main.id}/output/individual/
    aws s3 ls s3://${aws_s3_bucket.main.id}/output/batch/
    
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    💰 COST OPTIMIZATION:
    
    Current: ${var.batch_use_spot ? "Spot instances (up to 90% savings) ✅" : "On-demand instances"}
    
    To enable Spot instances (up to 90% savings):
    Set batch_use_spot = true in terraform.tfvars
    
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  EOT
}
