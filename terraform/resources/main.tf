provider "aws" {
  region = "us-east-1"
}

terraform {
  backend "local" {
    path = "$${path.root()}/state/terraform.tfstate"
  }
}

locals {
  db_name         = "granica"
  env             = "granica"
  db_subnet_group = "lab-us-east-1-dev-rds-db"
}


######################
# DATABASE
########

module "databse" {
  source = "../modules/database/"

  env             = local.env
  db_name         = local.db_name
  db_subnet_group = local.db_subnet_group

  db_password = aws_secretsmanager_secret_version.db_password_string.secret_string

  aurora_instance_count = 1
  instance_class        = "db.t4g.medium"

  skip_final_snapshot = true
  deletion_protection = false
}

resource "random_password" "db_password" {
  length  = 24
  special = false
  lifecycle {
    prevent_destroy = false
  }
}

resource "aws_secretsmanager_secret" "db_password" {
  name = "${local.env}-aurora-password"
  lifecycle {
    prevent_destroy = false
  }
}

resource "aws_secretsmanager_secret_version" "db_password_string" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = random_password.db_password.result
  lifecycle {
    prevent_destroy = false
  }
}


#######################
## OBJECT STORE
#########

module "object_store" {
  source = "../modules/s3/"

  env = local.env
}
