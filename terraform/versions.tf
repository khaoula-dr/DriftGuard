terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = { source = "hashicorp/aws" }
  }

  # Paramètres du backend dans backend.hcl (non versionné, car il contient
  # l'identifiant de compte). Voir backend.hcl.example.
  backend "s3" {}
}

provider "aws" {
  region = "eu-north-1"
}
