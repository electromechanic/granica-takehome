terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

resource "aws_rds_cluster" "database" {
  cluster_identifier = "${var.env}-aurora"

  engine         = var.engine
  engine_version = var.engine_version

  db_subnet_group_name   = var.db_subnet_group
  availability_zones     = data.aws_subnet.subnet.*.availability_zone
  vpc_security_group_ids = local.security_groups

  database_name   = var.db_name
  master_username = "master"
  master_password = var.db_password

  backup_retention_period      = var.backup_retention_period
  preferred_backup_window      = var.preferred_backup_window
  preferred_maintenance_window = var.preferred_maintenance_window
  apply_immediately            = var.apply_immediately
  deletion_protection          = var.deletion_protection
  skip_final_snapshot          = var.skip_final_snapshot
  final_snapshot_identifier    = "${var.db_name}-final"
}

resource "aws_rds_cluster_instance" "cluster_instances" {
  count = length(data.aws_subnet.subnet.*.availability_zone)

  identifier         = "${var.env}-aurora-cluster-${count.index}"
  cluster_identifier = aws_rds_cluster.database.id

  instance_class       = var.instance_class
  engine               = aws_rds_cluster.database.engine
  engine_version       = aws_rds_cluster.database.engine_version
  db_subnet_group_name = var.db_subnet_group

  monitoring_role_arn = aws_iam_role.monitoring_role.arn
  monitoring_interval = "60"
}

resource "aws_security_group" "allow_vpc" {
  name        = "${var.db_name}-vpc-access"
  description = "Allows access from addresses inside VPC"
  vpc_id      = data.aws_vpc.current.id

  ingress {
    description = "Connections from VPC"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.current.cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_iam_role" "monitoring_role" {
  name = "${var.env}-rds-monitoring"

  assume_role_policy = data.aws_iam_policy_document.rds_trust_policy.json
}

resource "aws_iam_role_policy_attachment" "monitor_policy_attach" {
  role       = aws_iam_role.monitoring_role.name
  policy_arn = data.aws_iam_policy.rds_monitoring.arn
}


data "aws_db_subnet_group" "database" {
  name = var.db_subnet_group
}

data "aws_subnet" "subnet" {
  # count = length(local.subnets)
  # Currently only 3 AZs can be specified for HA Aurora
  count = var.aurora_instance_count
  filter {
    name   = "subnet-id"
    values = [local.subnets[count.index]]
  }
}

data "aws_vpc" "current" {
  id = data.aws_db_subnet_group.database.vpc_id
}

data "aws_iam_policy_document" "rds_trust_policy" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["monitoring.rds.amazonaws.com"]
    }
  }
}

data "aws_iam_policy" "rds_monitoring" {
  name = "AmazonRDSEnhancedMonitoringRole"
}


locals {
  subnets         = tolist(data.aws_db_subnet_group.database.subnet_ids)
  security_groups = concat([aws_security_group.allow_vpc.id], var.additional_security_groups)
}

