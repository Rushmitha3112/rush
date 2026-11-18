resource "aws_s3_bucket" "raw" {
  bucket = "${local.name}-raw-${data.aws_caller_identity.me.account_id}"
}

resource "aws_s3_bucket" "curated" {
  bucket = "${local.name}-curated-${data.aws_caller_identity.me.account_id}"
}

resource "aws_s3_bucket" "artifacts" {
  bucket = "${local.name}-artifacts-${data.aws_caller_identity.me.account_id}"
}

resource "aws_s3_bucket_public_access_block" "all" {
  for_each                = { raw = aws_s3_bucket.raw.id, curated = aws_s3_bucket.curated.id, artifacts = aws_s3_bucket.artifacts.id }
  bucket                  = each.value
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# raw is the replay source for backfills, so keep versions
resource "aws_s3_bucket_versioning" "raw" {
  bucket = aws_s3_bucket.raw.id
  versioning_configuration { status = "Enabled" }
}

# raw drops are only re-read for backfills; after 90 days they can go cold
resource "aws_s3_bucket_lifecycle_configuration" "raw" {
  bucket = aws_s3_bucket.raw.id
  rule {
    id     = "cold-after-90d"
    status = "Enabled"
    filter {}
    transition {
      days          = 90
      storage_class = "GLACIER_IR"
    }
    noncurrent_version_expiration { noncurrent_days = 30 }
  }
}
