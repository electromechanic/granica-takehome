terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

data "aws_region" "current" {}

locals {
  region = data.aws_region.current.name
}


resource "aws_s3_bucket" "data_lake" {
  bucket = "${var.env}-${local.region}-data-lake"
}

resource "aws_s3_bucket_logging" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  target_bucket = aws_s3_bucket.data_lake.id
  target_prefix = "bucket_logs/"
}


