# Sample RDS Database Configuration

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "allocated_storage" {
  description = "Storage size in GB"
  type        = number
  default     = 20
}

resource "aws_db_instance" "postgres" {
  identifier        = "myapp-db"
  engine            = "postgres"
  engine_version    = "14.7"
  instance_class    = var.db_instance_class
  allocated_storage = var.allocated_storage
  storage_type      = "gp2"

  db_name  = "myapp"
  username = "admin"
  password = "changeme123" # Use secrets in production!

  multi_az            = false
  publicly_accessible = false
  skip_final_snapshot = true

  tags = {
    Name        = "MyApp Database"
    Environment = "Production"
  }
}
