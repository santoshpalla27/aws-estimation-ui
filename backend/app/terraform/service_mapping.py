"""
Helper function to map Terraform resource types to AWS service codes.
"""

# Mapping of Terraform resource types to AWS service codes
RESOURCE_TYPE_TO_SERVICE = {
    # EC2
    "aws_instance": "AmazonEC2",
    "aws_ebs_volume": "AmazonEBS",
    
    # RDS
    "aws_db_instance": "AmazonRDS",
    
    # S3
    "aws_s3_bucket": "AmazonS3",
    
    # Lambda
    "aws_lambda_function": "AWSLambda",
    
    # VPC (not priced)
    "aws_vpc": "AmazonVPC",
    "aws_subnet": "AmazonVPC",
    "aws_security_group": "AmazonVPC",
}


def get_service_code(resource_type: str) -> str:
    """
    Get AWS service code for a Terraform resource type.
    
    Args:
        resource_type: Terraform resource type (e.g., "aws_instance")
    
    Returns:
        AWS service code (e.g., "AmazonEC2")
    
    Raises:
        ValueError: If resource type is unknown
    """
    service_code = RESOURCE_TYPE_TO_SERVICE.get(resource_type)
    
    if not service_code:
        raise ValueError(f"Unknown resource type: {resource_type}")
    
    return service_code
