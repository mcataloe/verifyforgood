variable "region" {
  default = "us-east-1"
}

variable "domain_name" {
  description = "API domain name"
}

variable "env" {
  description = "Environment name"
  type        = string
}
