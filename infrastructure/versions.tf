terraform {
  backend "s3" {
    bucket         = "charitystatusapi-dev"
    key            = "terraform/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "charitystatusapi-dev"
    # encrypt        = true
  }

  required_version = ">= 1.14.6" # Specify the minimum Terraform version.

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.35.1" # Constrain the provider version for compatibility.
    }
  }
}