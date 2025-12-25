# Sample Multi-Service Configuration

locals {
  environment = "production"
  app_name    = "myapp"
}

# EC2 Instances with count
resource "aws_instance" "app_servers" {
  count         = 3
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.small"

  tags = {
    Name        = "${local.app_name}-server-${count.index}"
    Environment = local.environment
  }
}

# S3 Bucket
resource "aws_s3_bucket" "data" {
  bucket = "${local.app_name}-data-bucket"

  tags = {
    Name        = "Data Bucket"
    Environment = local.environment
  }
}

# Lambda Function
resource "aws_lambda_function" "processor" {
  function_name = "${local.app_name}-processor"
  runtime       = "python3.9"
  handler       = "index.handler"
  memory_size   = 256

  # These are estimates for cost calculation
  estimated_invocations = 500000
  estimated_duration_ms = 2000

  filename = "lambda.zip"

  tags = {
    Name        = "Data Processor"
    Environment = local.environment
  }
}

# RDS Database
resource "aws_db_instance" "main" {
  identifier        = "${local.app_name}-db"
  engine            = "mysql"
  instance_class    = "db.t3.medium"
  allocated_storage = 50
  storage_type      = "gp3"
  multi_az          = true

  tags = {
    Name        = "Main Database"
    Environment = local.environment
  }
}
