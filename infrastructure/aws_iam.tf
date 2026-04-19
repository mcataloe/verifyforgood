
#############################################
# IAM ROLE FOR LAMBDAS
#############################################

resource "aws_iam_role" "lambda_role" {
  name = local.lambda_role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "basic_lambda" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_vpc_access" {
  count      = var.platform_postgres_enabled ? 1 : 0
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy" "lambda_data_access" {
  name = local.lambda_data_policy_name
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      [
        {
          # TODO: Narrow this to least-privilege resource actions per Form 990 stage.
          Action = [
            "s3:*",
            "sqs:*",
            "athena:*",
            "glue:*"
          ]
          Effect   = "Allow"
          Resource = "*"
        },
        {
          Action = [
            "lambda:InvokeFunction"
          ]
          Effect = "Allow"
          Resource = [
            aws_lambda_function.form990_orchestrator.arn
          ]
        },
      ],
      var.platform_postgres_enabled ? [
        {
          Action = [
            "secretsmanager:GetSecretValue",
            "secretsmanager:DescribeSecret"
          ]
          Effect = "Allow"
          Resource = [
            local.platform_postgres_secret_arn_resolved
          ]
        }
      ] : [],
      var.platform_nonprofit_postgres_enabled ? [
        {
          Action = [
            "secretsmanager:GetSecretValue",
            "secretsmanager:DescribeSecret"
          ]
          Effect = "Allow"
          Resource = [
            trim(var.platform_nonprofit_postgres_secret_arn, " ")
          ]
        }
      ] : [],
      var.platform_postgres_enabled && trim(var.platform_postgres_secret_kms_key_arn, " ") != "" ? [
        {
          Action = [
            "kms:Decrypt"
          ]
          Effect = "Allow"
          Resource = [
            trim(var.platform_postgres_secret_kms_key_arn, " ")
          ]
        }
      ] : [],
      var.platform_nonprofit_postgres_enabled && trim(var.platform_nonprofit_postgres_secret_kms_key_arn, " ") != "" ? [
        {
          Action = [
            "kms:Decrypt"
          ]
          Effect = "Allow"
          Resource = [
            trim(var.platform_nonprofit_postgres_secret_kms_key_arn, " ")
          ]
        }
      ] : [],
    )
  })
}
