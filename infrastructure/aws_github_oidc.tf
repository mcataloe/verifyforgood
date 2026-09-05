data "aws_caller_identity" "github_deploy" {
  count = var.github_oidc_deploy_role_enabled ? 1 : 0
}

resource "aws_iam_openid_connect_provider" "github_actions" {
  count = var.github_oidc_deploy_role_enabled && var.github_oidc_manage_provider ? 1 : 0

  url = "https://token.actions.githubusercontent.com"

  client_id_list = ["sts.amazonaws.com"]

  tags = local.platform_common_tags
}

locals {
  github_oidc_provider_arn_effective = !var.github_oidc_deploy_role_enabled ? "" : (
    var.github_oidc_manage_provider ? aws_iam_openid_connect_provider.github_actions[0].arn : trim(var.github_oidc_provider_arn, " ")
  )

  github_project_role_arns = var.github_oidc_deploy_role_enabled ? [
    "arn:aws:iam::${data.aws_caller_identity.github_deploy[0].account_id}:role/${local.namespace}-${local.platform}-*",
    "arn:aws:iam::${data.aws_caller_identity.github_deploy[0].account_id}:role/charitystatusapi-${local.environment_slug}-*",
    "arn:aws:iam::${data.aws_caller_identity.github_deploy[0].account_id}:role/${var.github_dev_deploy_role_name}",
  ] : []

  github_project_policy_arns = var.github_oidc_deploy_role_enabled ? [
    "arn:aws:iam::${data.aws_caller_identity.github_deploy[0].account_id}:policy/${local.namespace}-${local.platform}-*",
    "arn:aws:iam::${data.aws_caller_identity.github_deploy[0].account_id}:policy/charitystatusapi-${local.environment_slug}-*",
  ] : []
}

resource "aws_iam_role" "github_dev_deploy" {
  count = var.github_oidc_deploy_role_enabled ? 1 : 0

  name = var.github_dev_deploy_role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "GitHubActionsDevEnvironment"
        Effect = "Allow"
        Principal = {
          Federated = local.github_oidc_provider_arn_effective
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
            "token.actions.githubusercontent.com:sub" = "repo:${var.github_repository}:environment:${var.github_environment_name}"
          }
        }
      }
    ]
  })

  tags = local.platform_common_tags
}

resource "aws_iam_role_policy" "github_dev_deploy" {
  count = var.github_oidc_deploy_role_enabled ? 1 : 0

  name = "${var.github_dev_deploy_role_name}-terraform"
  role = aws_iam_role.github_dev_deploy[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "TerraformStateBucket"
        Effect = "Allow"
        Action = [
          "s3:GetBucketLocation",
          "s3:GetBucketVersioning",
          "s3:ListBucket"
        ]
        Resource = ["arn:aws:s3:::${var.terraform_state_bucket_name}"]
      },
      {
        Sid    = "TerraformStateObjects"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = ["arn:aws:s3:::${var.terraform_state_bucket_name}/*"]
      },
      {
        Sid    = "TerraformStateLock"
        Effect = "Allow"
        Action = [
          "dynamodb:DescribeTable",
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:DeleteItem"
        ]
        Resource = [
          "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.github_deploy[0].account_id}:table/${var.terraform_state_lock_table_name}"
        ]
      },
      {
        Sid    = "DevInfrastructureServices"
        Effect = "Allow"
        Action = [
          "acm:*",
          "apigateway:*",
          "application-autoscaling:*",
          "athena:*",
          "cloudwatch:*",
          "dynamodb:*",
          "ec2:*",
          "ecr:*",
          "ecs:*",
          "elasticloadbalancing:*",
          "events:*",
          "glue:*",
          "kms:*",
          "lambda:*",
          "logs:*",
          "rds:*",
          "route53:*",
          "s3:*",
          "secretsmanager:*",
          "sqs:*",
          "ssm:*",
          "states:*"
        ]
        Resource = "*"
      },
      {
        Sid    = "ManageProjectIamRoles"
        Effect = "Allow"
        Action = [
          "iam:CreateRole",
          "iam:DeleteRole",
          "iam:GetRole",
          "iam:TagRole",
          "iam:UntagRole",
          "iam:UpdateAssumeRolePolicy",
          "iam:PutRolePolicy",
          "iam:GetRolePolicy",
          "iam:DeleteRolePolicy",
          "iam:AttachRolePolicy",
          "iam:DetachRolePolicy",
          "iam:ListAttachedRolePolicies",
          "iam:ListRolePolicies",
          "iam:PassRole"
        ]
        Resource = local.github_project_role_arns
      },
      {
        Sid    = "ManageGitHubOidcProvider"
        Effect = "Allow"
        Action = [
          "iam:CreateOpenIDConnectProvider",
          "iam:GetOpenIDConnectProvider",
          "iam:DeleteOpenIDConnectProvider",
          "iam:UpdateOpenIDConnectProviderThumbprint",
          "iam:AddClientIDToOpenIDConnectProvider",
          "iam:RemoveClientIDFromOpenIDConnectProvider",
          "iam:TagOpenIDConnectProvider",
          "iam:UntagOpenIDConnectProvider"
        ]
        Resource = "*"
      },
      {
        Sid    = "ReadManagedPolicies"
        Effect = "Allow"
        Action = [
          "iam:GetPolicy",
          "iam:GetPolicyVersion",
          "iam:ListPolicyVersions"
        ]
        Resource = concat(
          local.github_project_policy_arns,
          [
            "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
          ]
        )
      },
      {
        Sid      = "CreateRequiredServiceLinkedRoles"
        Effect   = "Allow"
        Action   = "iam:CreateServiceLinkedRole"
        Resource = "*"
      }
    ]
  })
}
