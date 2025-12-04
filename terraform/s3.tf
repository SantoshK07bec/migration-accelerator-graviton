# S3 Bucket for SBOM files and results
resource "aws_s3_bucket" "main" {
  bucket        = "${var.bucket_name}-${random_string.random.result}"
  force_destroy = true

  tags = {
    Name = "graviton-validator-bucket"
  }
}

# S3 Event Notifications - Enable EventBridge for Lambda triggers
resource "aws_s3_bucket_notification" "main" {
  bucket      = aws_s3_bucket.main.id
  eventbridge = true
}

# S3 Access Logging - logs stored in same bucket under access-logs/ prefix
resource "aws_s3_bucket_logging" "main" {
  bucket = aws_s3_bucket.main.id

  target_bucket = aws_s3_bucket.main.id
  target_prefix = "access-logs/"
}

resource "aws_s3_bucket_versioning" "main" {
  bucket = aws_s3_bucket.main.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "main" {
  bucket = aws_s3_bucket.main.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.s3.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "main" {
  bucket = aws_s3_bucket.main.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "main" {
  bucket = aws_s3_bucket.main.id

  rule {
    id     = "delete_old_objects"
    status = "Enabled"

    filter {}

    expiration {
      days = 90
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }

    # Abort incomplete multipart uploads after 7 days
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  # Separate rule for access logs cleanup
  rule {
    id     = "delete_old_access_logs"
    status = "Enabled"

    filter {
      prefix = "access-logs/"
    }

    expiration {
      days = 30
    }
  }
}

# Create folder structure
resource "aws_s3_object" "input_individual" {
  bucket  = aws_s3_bucket.main.id
  key     = "input/individual/"
  content = ""
}

resource "aws_s3_object" "input_batch" {
  bucket  = aws_s3_bucket.main.id
  key     = "input/batch/"
  content = ""
}

resource "aws_s3_object" "output_individual" {
  bucket  = aws_s3_bucket.main.id
  key     = "output/individual/"
  content = ""
}

resource "aws_s3_object" "output_batch" {
  bucket  = aws_s3_bucket.main.id
  key     = "output/batch/"
  content = ""
}

resource "aws_s3_object" "code" {
  bucket  = aws_s3_bucket.main.id
  key     = "code/"
  content = ""
}

# Upload migration-accelerator-graviton tool
resource "aws_s3_object" "validator_tool" {
  bucket      = aws_s3_bucket.main.id
  key         = "code/migration-accelerator-graviton.zip"
  source      = data.archive_file.zip_validation_tool.output_path
  source_hash = data.archive_file.zip_validation_tool.output_base64sha256

  depends_on = [
    aws_s3_object.code,
    data.archive_file.zip_validation_tool
  ]
}
