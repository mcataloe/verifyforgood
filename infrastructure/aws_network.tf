data "aws_availability_zones" "available" {
  count = var.environment_network_enabled ? 1 : 0
  state = "available"
}

locals {
  environment_public_subnet_count  = var.environment_network_enabled ? min(2, length(var.environment_public_subnet_cidrs)) : 0
  environment_private_subnet_count = var.environment_network_enabled ? min(2, length(var.environment_private_subnet_cidrs)) : 0

  environment_vpc_id = var.environment_network_enabled ? aws_vpc.environment[0].id : ""
  environment_public_subnet_ids = var.environment_network_enabled ? [
    for subnet in aws_subnet.environment_public : subnet.id
  ] : []
  environment_private_subnet_ids = var.environment_network_enabled ? [
    for subnet in aws_subnet.environment_private : subnet.id
  ] : []

  api_ecs_vpc_id_effective = var.environment_network_enabled ? local.environment_vpc_id : var.api_ecs_vpc_id
  api_ecs_public_subnet_ids_effective = var.environment_network_enabled ? local.environment_public_subnet_ids : var.api_ecs_public_subnet_ids
  api_ecs_private_subnet_ids_effective = var.environment_network_enabled ? local.environment_private_subnet_ids : var.api_ecs_private_subnet_ids

  platform_postgres_vpc_id_effective = var.environment_network_enabled ? local.environment_vpc_id : var.platform_postgres_vpc_id
  platform_postgres_private_subnet_ids_effective = var.environment_network_enabled ? local.environment_private_subnet_ids : var.platform_postgres_private_subnet_ids

  monthly_ingest_private_subnet_ids_effective = var.environment_network_enabled ? local.environment_private_subnet_ids : var.monthly_ingest_private_subnet_ids
  monthly_ingest_task_security_group_ids_effective = var.environment_network_enabled ? [aws_security_group.monthly_ingest[0].id] : var.monthly_ingest_task_security_group_ids
}

resource "aws_vpc" "environment" {
  count = var.environment_network_enabled ? 1 : 0

  cidr_block           = var.environment_vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(local.platform_common_tags, {
    Name = "${local.namespace}-${local.platform}-vpc-${local.environment_slug}-${local.region_short}"
  })
}

resource "aws_internet_gateway" "environment" {
  count = var.environment_network_enabled ? 1 : 0

  vpc_id = aws_vpc.environment[0].id

  tags = merge(local.platform_common_tags, {
    Name = "${local.namespace}-${local.platform}-igw-${local.environment_slug}-${local.region_short}"
  })
}

resource "aws_subnet" "environment_public" {
  count = local.environment_public_subnet_count

  vpc_id                  = aws_vpc.environment[0].id
  cidr_block              = var.environment_public_subnet_cidrs[count.index]
  availability_zone       = data.aws_availability_zones.available[0].names[count.index]
  map_public_ip_on_launch = false

  tags = merge(local.platform_common_tags, {
    Name = "${local.namespace}-${local.platform}-public-${count.index + 1}-${local.environment_slug}-${local.region_short}"
    Tier = "public"
  })
}

resource "aws_subnet" "environment_private" {
  count = local.environment_private_subnet_count

  vpc_id                  = aws_vpc.environment[0].id
  cidr_block              = var.environment_private_subnet_cidrs[count.index]
  availability_zone       = data.aws_availability_zones.available[0].names[count.index]
  map_public_ip_on_launch = false

  tags = merge(local.platform_common_tags, {
    Name = "${local.namespace}-${local.platform}-private-${count.index + 1}-${local.environment_slug}-${local.region_short}"
    Tier = "private"
  })
}

resource "aws_route_table" "environment_public" {
  count = var.environment_network_enabled ? 1 : 0

  vpc_id = aws_vpc.environment[0].id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.environment[0].id
  }

  tags = merge(local.platform_common_tags, {
    Name = "${local.namespace}-${local.platform}-public-rt-${local.environment_slug}-${local.region_short}"
  })
}

resource "aws_route_table_association" "environment_public" {
  count = local.environment_public_subnet_count

  subnet_id      = aws_subnet.environment_public[count.index].id
  route_table_id = aws_route_table.environment_public[0].id
}

resource "aws_eip" "environment_nat" {
  count = var.environment_network_enabled && var.environment_single_nat_gateway_enabled ? 1 : 0

  domain = "vpc"

  tags = merge(local.platform_common_tags, {
    Name = "${local.namespace}-${local.platform}-nat-eip-${local.environment_slug}-${local.region_short}"
  })

  depends_on = [aws_internet_gateway.environment]
}

resource "aws_nat_gateway" "environment" {
  count = var.environment_network_enabled && var.environment_single_nat_gateway_enabled ? 1 : 0

  allocation_id = aws_eip.environment_nat[0].id
  subnet_id     = aws_subnet.environment_public[0].id

  tags = merge(local.platform_common_tags, {
    Name = "${local.namespace}-${local.platform}-nat-${local.environment_slug}-${local.region_short}"
  })

  depends_on = [aws_internet_gateway.environment]
}

resource "aws_route_table" "environment_private" {
  count = var.environment_network_enabled ? 1 : 0

  vpc_id = aws_vpc.environment[0].id

  dynamic "route" {
    for_each = var.environment_single_nat_gateway_enabled ? [1] : []
    content {
      cidr_block     = "0.0.0.0/0"
      nat_gateway_id = aws_nat_gateway.environment[0].id
    }
  }

  tags = merge(local.platform_common_tags, {
    Name = "${local.namespace}-${local.platform}-private-rt-${local.environment_slug}-${local.region_short}"
  })
}

resource "aws_route_table_association" "environment_private" {
  count = local.environment_private_subnet_count

  subnet_id      = aws_subnet.environment_private[count.index].id
  route_table_id = aws_route_table.environment_private[0].id
}

resource "aws_security_group" "monthly_ingest" {
  count = var.environment_network_enabled ? 1 : 0

  name        = "${local.namespace}-${local.platform}-ingest-task-sg-${local.environment_slug}-${local.region_short}"
  description = "Private ECS ingest task security group. Egress uses the environment NAT gateway for IRS and future state sources."
  vpc_id      = aws_vpc.environment[0].id

  egress {
    description = "Allow outbound HTTPS and AWS service access through the private route table."
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.platform_common_tags
}

resource "aws_vpc_endpoint" "s3_gateway" {
  count = var.environment_network_enabled && var.environment_s3_gateway_endpoint_enabled ? 1 : 0

  vpc_id            = aws_vpc.environment[0].id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.environment_private[0].id]

  tags = merge(local.platform_common_tags, {
    Name = "${local.namespace}-${local.platform}-s3-gateway-${local.environment_slug}-${local.region_short}"
  })
}
