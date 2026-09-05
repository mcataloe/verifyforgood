# Keep the existing HTTPS listener default-forward behavior for compatibility
# while introducing the customer-facing /api/* route. When the frontend is
# deployed, the listener default action can move to the frontend target without
# changing the public API URL.
resource "aws_lb_listener_rule" "api_prefix" {
  count = var.api_ecs_enabled ? 1 : 0

  listener_arn = aws_lb_listener.api_https[0].arn
  priority     = 10

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api[0].arn
  }

  condition {
    path_pattern {
      values = ["/api/*"]
    }
  }

  transform {
    type = "url-rewrite"

    url_rewrite_config {
      rewrite {
        regex   = "^/api/(.*)$"
        replace = "/$1"
      }
    }
  }
}
