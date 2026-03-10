#############################################
# ACM CERTIFICATE
#############################################

locals {
  base_domain_name      = trim(var.domain_name, ".")
  computed_domain_name  = var.env == "prod" ? local.base_domain_name : "${var.env}.${local.base_domain_name}"
  route53_zone_name     = "${local.base_domain_name}."
}

data "aws_route53_zone" "selected" {
  name         = local.route53_zone_name
  private_zone = false
}

resource "aws_acm_certificate" "cert" {
  domain_name       = local.computed_domain_name
  validation_method = "DNS"
}

resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.cert.domain_validation_options :
    dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  zone_id = data.aws_route53_zone.selected.zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.record]
  ttl     = 60
}

resource "aws_acm_certificate_validation" "cert" {
  certificate_arn         = aws_acm_certificate.cert.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}

#############################################
# API CUSTOM DOMAIN
#############################################

resource "aws_api_gateway_domain_name" "api_domain" {
  domain_name = local.computed_domain_name

  certificate_arn = aws_acm_certificate_validation.cert.certificate_arn
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

  zone_id = data.aws_route53_zone.selected.zone_id
  name    = local.computed_domain_name
  type    = "A"

  alias {
    name                   = aws_api_gateway_domain_name.api_domain.cloudfront_domain_name
    zone_id                = aws_api_gateway_domain_name.api_domain.cloudfront_zone_id
    evaluate_target_health = false
  }
}
