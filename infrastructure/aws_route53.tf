#############################################
# ACM CERTIFICATE
#############################################

locals {
  base_domain_name     = trim(local.domain_name, ".")
  computed_domain_name = var.environment == "prod" ? local.base_domain_name : "${var.environment}.${local.base_domain_name}"
  route53_zone_name    = var.route53_zone_name != "" ? var.route53_zone_name : "${local.base_domain_name}."
  enable_custom_domain = var.enable_custom_domain && local.base_domain_name != ""
}

data "aws_route53_zone" "selected" {
  count = local.enable_custom_domain ? 1 : 0
  name  = local.route53_zone_name

  private_zone = false
}

locals {
  route53_zone_id = local.enable_custom_domain ? data.aws_route53_zone.selected[0].zone_id : null
}

resource "aws_acm_certificate" "cert" {
  count             = local.enable_custom_domain ? 1 : 0
  domain_name       = local.computed_domain_name
  validation_method = "DNS"
}

resource "aws_route53_record" "cert_validation" {
  for_each = local.enable_custom_domain ? {
    for dvo in aws_acm_certificate.cert[0].domain_validation_options :
    dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  } : {}

  zone_id = local.route53_zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.record]
  ttl     = 60
}

resource "aws_acm_certificate_validation" "cert" {
  count                   = local.enable_custom_domain ? 1 : 0
  certificate_arn         = aws_acm_certificate.cert[0].arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}

#############################################
# API CUSTOM DOMAIN
#############################################

resource "aws_api_gateway_domain_name" "api_domain" {
  count       = local.enable_custom_domain ? 1 : 0
  domain_name = local.computed_domain_name

  certificate_arn = aws_acm_certificate_validation.cert[0].certificate_arn
}

resource "aws_api_gateway_base_path_mapping" "mapping" {
  count = local.enable_custom_domain ? 1 : 0

  api_id      = aws_api_gateway_rest_api.irs_api.id
  stage_name  = aws_api_gateway_stage.environment.stage_name
  domain_name = aws_api_gateway_domain_name.api_domain[0].domain_name
}

#############################################
# ROUTE53 RECORD
#############################################

resource "aws_route53_record" "api_record" {
  count   = local.enable_custom_domain ? 1 : 0
  zone_id = local.route53_zone_id
  name    = local.computed_domain_name
  type    = "A"

  alias {
    name                   = aws_api_gateway_domain_name.api_domain[0].cloudfront_domain_name
    zone_id                = aws_api_gateway_domain_name.api_domain[0].cloudfront_zone_id
    evaluate_target_health = false
  }
}
