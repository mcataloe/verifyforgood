terraform {
  backend "s3" {
    bucket         = "charitystatusapi-dev"
    key            = "terraform/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "charitystatusapi-dev"
  }

  required_version = ">= 1.14.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.35.1"
    }
  }
}