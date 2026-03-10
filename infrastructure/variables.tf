variable "region" {
  default = "us-east-1"
}

variable "domain_name" {
  description = "API domain name"
}

variable "hosted_zone_id" {
  description = "Route53 hosted zone id"
}

variable "env" {
  description = "Environment name"
  type        = string
}