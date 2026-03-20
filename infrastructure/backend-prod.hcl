# Backend bootstrap resources remain pinned to legacy names until state migration is planned.
# They are intentionally not switched by the Terraform resource naming strategy toggle.
bucket         = "charitystatusapi-tfstate"
key            = "terraform/terraform.tfstate"
region         = "us-east-1"
dynamodb_table = "charitystatusapi-tf-locks"
