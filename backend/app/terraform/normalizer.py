"""
Resource normalizer.
Converts Terraform resources to canonical format.
"""
import logging
from typing import Dict, List, Optional
from copy import deepcopy

from app.config import settings

logger = logging.getLogger(__name__)


class ResourceNormalizer:
    """
    Normalizes Terraform resources into canonical format.
    """
    
    # Mapping of Terraform resource types to AWS services
    RESOURCE_TYPE_MAP = {
        # EC2
        "aws_instance": {"service": "AmazonEC2", "type": "instance"},
        "aws_ebs_volume": {"service": "AmazonEBS", "type": "volume"},
        
        # RDS
        "aws_db_instance": {"service": "AmazonRDS", "type": "db_instance"},
        
        # S3
        "aws_s3_bucket": {"service": "AmazonS3", "type": "bucket"},
        
        # Lambda
        "aws_lambda_function": {"service": "AWSLambda", "type": "function"},
        
        # VPC (not priced but tracked)
        "aws_vpc": {"service": "AmazonVPC", "type": "vpc"},
        "aws_subnet": {"service": "AmazonVPC", "type": "subnet"},
        "aws_security_group": {"service": "AmazonVPC", "type": "security_group"},
    }
    
    def __init__(self):
        self.warnings = []
    
    def expand_count(self, resource: Dict) -> List[Dict]:
        """
        Expand resources with count meta-argument.
        
        Args:
            resource: Resource dictionary
        
        Returns:
            List of expanded resources
        """
        count = resource.get("attributes", {}).get("count")
        
        if count is None:
            return [resource]
        
        # Convert count to integer
        try:
            count_int = int(count)
        except (ValueError, TypeError):
            logger.warning(f"Invalid count value: {count}")
            return [resource]
        
        # CRITICAL: Fail on expansion limit exceeded (no silent truncation)
        if count_int > settings.max_count_expansion:
            error_msg = (
                f"Count {count_int} exceeds max_count_expansion={settings.max_count_expansion}. "
                f"This would cause massive cost underestimation. "
                f"Increase MAX_COUNT_EXPANSION environment variable or reduce count."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Create copies
        expanded = []
        for i in range(count_int):
            resource_copy = deepcopy(resource)
            resource_copy["name"] = f"{resource['name']}[{i}]"
            resource_copy["count_index"] = i
            expanded.append(resource_copy)
        
        logger.info(f"Expanded count={count_int} for {resource['name']}")
        return expanded
    
    def expand_for_each(self, resource: Dict) -> List[Dict]:
        """
        Expand resources with for_each meta-argument.
        
        Args:
            resource: Resource dictionary
        
        Returns:
            List of expanded resources
        """
        for_each = resource.get("attributes", {}).get("for_each")
        
        if for_each is None:
            return [resource]
        
        # for_each can be a map or set
        if isinstance(for_each, dict):
            items = for_each.items()
        elif isinstance(for_each, (list, set)):
            items = [(item, item) for item in for_each]
        else:
            logger.warning(f"Invalid for_each value: {for_each}")
            return [resource]
        
        # CRITICAL: Fail on expansion limit exceeded (no silent truncation)
        if len(items) > settings.max_for_each_expansion:
            error_msg = (
                f"for_each size {len(items)} exceeds max_for_each_expansion={settings.max_for_each_expansion}. "
                f"This would cause cost underestimation. "
                f"Increase MAX_FOR_EACH_EXPANSION environment variable or reduce for_each size."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Create copies
        expanded = []
        for key, value in items:
            resource_copy = deepcopy(resource)
            resource_copy["name"] = f"{resource['name']}[{key}]"
            resource_copy["for_each_key"] = key
            resource_copy["for_each_value"] = value
            expanded.append(resource_copy)
        
        logger.info(f"Expanded for_each with {len(items)} items for {resource['name']}")
        return expanded
    
    def normalize_resource(self, resource: Dict) -> Optional[Dict]:
        """
        Normalize a Terraform resource to canonical format.
        
        Args:
            resource: Raw Terraform resource
        
        Returns:
            Normalized resource or None if unsupported
        """
        resource_type = resource.get("type")
        
        if resource_type not in self.RESOURCE_TYPE_MAP:
            logger.warning(f"Unsupported resource type: {resource_type}")
            self.warnings.append(f"Unsupported resource type: {resource_type}")
            return None
        
        mapping = self.RESOURCE_TYPE_MAP[resource_type]
        attributes = resource.get("attributes", {})
        
        # Extract region (may be in provider or resource)
        region = attributes.get("region") or attributes.get("availability_zone", "us-east-1")
        if isinstance(region, str) and region.endswith(("a", "b", "c", "d", "e", "f")):
            # Strip AZ suffix to get region
            region = region[:-1]
        
        # Build normalized resource
        normalized = {
            "provider": "aws",
            "service": mapping["service"],
            "type": mapping["type"],
            "resource_type": resource_type,
            "name": resource.get("name"),
            "region": region,
            "attributes": self.normalize_attributes(resource_type, attributes)
        }
        
        return normalized
    
    def normalize_attributes(self, resource_type: str, attributes: Dict) -> Dict:
        """
        Normalize resource attributes based on type.
        
        Args:
            resource_type: Terraform resource type
            attributes: Raw attributes
        
        Returns:
            Normalized attributes
        """
        # Type-specific normalization
        if resource_type == "aws_instance":
            # CRITICAL: Don't infer OS - require explicit specification
            operating_system = attributes.get("operating_system")
            if not operating_system:
                # Try to get from tags or fail
                tags = attributes.get("tags", {})
                operating_system = tags.get("OperatingSystem") or tags.get("OS")
            
            return {
                "instance_type": attributes.get("instance_type"),
                "ami": attributes.get("ami"),
                "tenancy": attributes.get("tenancy", "default"),
                "operating_system": operating_system or "Linux",  # Default to Linux only as fallback
            }
        
        elif resource_type == "aws_ebs_volume":
            return {
                "volume_type": attributes.get("type", "gp2"),
                "size": attributes.get("size", 100),
                "iops": attributes.get("iops", 0),
            }
        
        elif resource_type == "aws_db_instance":
            return {
                "instance_class": attributes.get("instance_class"),
                "engine": attributes.get("engine", "mysql"),
                "allocated_storage": attributes.get("allocated_storage", 20),
                "storage_type": attributes.get("storage_type", "gp2"),
                "deployment_option": "Multi-AZ" if attributes.get("multi_az") else "Single-AZ",
            }
        
        elif resource_type == "aws_s3_bucket":
            return {
                "storage_class": attributes.get("storage_class", "STANDARD"),
                "estimated_storage_gb": attributes.get("estimated_storage_gb", 100),
                "estimated_requests": attributes.get("estimated_requests", 10000),
            }
        
        elif resource_type == "aws_lambda_function":
            return {
                "memory_size": attributes.get("memory_size", 128),
                "estimated_invocations": attributes.get("estimated_invocations", 100000),
                "estimated_duration_ms": attributes.get("estimated_duration_ms", 1000),
            }
        
        # Default: return all attributes
        return attributes
    
    def infer_os_from_ami(self, ami: str) -> str:
        """
        Infer operating system from AMI ID or name.
        
        Args:
            ami: AMI ID or name
        
        Returns:
            Operating system name
        """
        ami_lower = ami.lower()
        
        if "windows" in ami_lower:
            return "Windows"
        elif "rhel" in ami_lower or "redhat" in ami_lower:
            return "RHEL"
        elif "suse" in ami_lower:
            return "SUSE"
        else:
            return "Linux"
    
    def normalize_all(self, resources: List[Dict]) -> List[Dict]:
        """
        Normalize all resources.
        
        Args:
            resources: List of raw Terraform resources
        
        Returns:
            List of normalized resources
        """
        normalized = []
        
        for resource in resources:
            # Expand count
            expanded_count = self.expand_count(resource)
            
            # Expand for_each
            expanded_all = []
            for res in expanded_count:
                expanded_all.extend(self.expand_for_each(res))
            
            # Normalize each expanded resource
            for res in expanded_all:
                normalized_res = self.normalize_resource(res)
                if normalized_res:
                    normalized.append(normalized_res)
        
        logger.info(f"Normalized {len(normalized)} resources from {len(resources)} raw resources")
        return normalized
