#############################################
# ACM CERTIFICATE
#############################################

resource "aws_acm_certificate" "cert" {
  domain_name       = var.domain_name
  validation_method = "DNS"
}

#############################################
# API CUSTOM DOMAIN
#############################################

resource "aws_api_gateway_domain_name" "api_domain" {
  domain_name = var.domain_name

  certificate_arn = aws_acm_certificate.cert.arn
}

resource "aws_api_gateway_base_path_mapping" "mapping" {

  api_id      = aws_api_gateway_rest_api.irs_api.id
  stage_name  = aws_api_gateway_stage.prod.stage_name
  domain_name = aws_api_gateway_domain_name.api_domain.domain_name
}

#############################################
# ROUTE53 RECORD
#############################################

resource "aws_route53_record" "api_record" {

  zone_id = var.hosted_zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = aws_api_gateway_domain_name.api_domain.cloudfront_domain_name
    zone_id                = aws_api_gateway_domain_name.api_domain.cloudfront_zone_id
    evaluate_target_health = false
  }
}
