terraform {
  backend "s3" {
  }

  required_version = ">= 1.14.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.35.1"
    }
  }
}

provider "aws" {
  region = var.aws_region
}
