terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = { source = "hashicorp/aws" }
  }
  # Backend S3 : à activer après création du bucket de state (ADR-004)
  # backend "s3" {
  #   bucket       = "<bucket-state-driftguard>"
  #   key          = "driftguard/terraform.tfstate"
  #   region       = "eu-north-1"
  #   use_lockfile = true
  # }
}

provider "aws" {
  region = "eu-north-1"
}
