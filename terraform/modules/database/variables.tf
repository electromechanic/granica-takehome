variable "env" {
  description = "Environment to deploy Aurora cluster"
  type        = string
}

variable "db_name" {
  description = "Name of database (alphanumeric characters only)"
}

variable "db_subnet_group" {
  description = "name of db subnet group"
}

variable "backup_retention_period" {
  description = "Number of days to keep backups"
  type        = number
  default     = 7
}

variable "engine" {
  description = "Database engine type"
  type        = string
  default     = "aurora-postgresql"
}

variable "engine_version" {
  description = "Engine version for database"
  type        = string
  default     = "14.6"
}

variable "preferred_backup_window" {
  description = "Preferred time of day to perform backup operation"
  type        = string
  default     = "09:38-10:08"
}

variable "preferred_maintenance_window" {
  description = "Preferred time of the week to perform maintenance"
  type        = string
  default     = "mon:07:00-mon:07:30"
}

variable "apply_immediately" {
  description = "Boolean to apply database changes immediately or wait for maintenance window"
  type        = bool
  default     = false
}

variable "deletion_protection" {
  description = "Deletion protection"
  type        = bool
  default     = true
}

variable "db_password" {
  description = "password for database"
  type        = string
}

variable "storage_encrypted" {
  description = "Enable/disable storage encryption"
  type        = bool
  default     = false
}


variable "additional_security_groups" {
  description = "List of additional security groups to add to the database"
  type        = list(any)
  default     = []
}

variable "skip_final_snapshot" {
  description = "Enable or disable final snapshot"
  type        = bool
  default     = false
}

variable "instance_class" {
  description = "Instance class for cluster nodes"
  type        = string
  default     = "db.r6g.large"
}

variable "aurora_instance_count" {
  description = "Count of HA instances in aurora cluster"
  type        = number
  default     = 3
}

variable "cloudwatch_log_exports" {
  description = "list of strings, type of logs to export to cloudwatch [audit, error, general, slowquery, postgreql]"
  type        = list(any)
  default     = []
}
