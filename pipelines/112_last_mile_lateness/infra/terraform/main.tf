terraform {
  required_version = ">= 1.6"
  required_providers {
    aws     = { source = "hashicorp/aws", version = "~> 5.70" }
    archive = { source = "hashicorp/archive", version = "~> 2.6" }
  }
  # backend "s3" {}  # configure per environment: terraform init -backend-config=env/dev.hcl
}

provider "aws" {
  region = var.region
  default_tags {
    tags = { project = "lastmile-lateness", env = var.env }
  }
}

locals {
  name = "lastmile-${var.env}"
}

data "aws_caller_identity" "me" {}
