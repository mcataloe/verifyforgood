
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

resource "aws_iam_role_policy" "lambda_data_access" {
  name = local.lambda_data_policy_name
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
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
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem"
        ]
        Effect = "Allow"
        Resource = [
          aws_dynamodb_table.profiles.arn,
          aws_dynamodb_table.organization_settings.arn,
          aws_dynamodb_table.control_plane.arn,
          "${aws_dynamodb_table.organization_settings.arn}/index/account_lookup",
          "${aws_dynamodb_table.control_plane.arn}/index/credential_lookup",
          "${aws_dynamodb_table.control_plane.arn}/index/entity_listing",
        ]
      }
    ]
  })
}
