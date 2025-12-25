# Sample EC2 Instance Configuration

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

resource "aws_instance" "web_server" {
  ami           = "ami-0c55b159cbfafe1f0"  # Amazon Linux 2
  instance_type = var.instance_type
  
  tags = {
    Name = "WebServer"
    Environment = "Production"
  }
}

resource "aws_ebs_volume" "data" {
  availability_zone = "${var.region}a"
  size              = 100
  type              = "gp3"
  
  tags = {
    Name = "DataVolume"
  }
}
