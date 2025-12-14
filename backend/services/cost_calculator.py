"""
Cost Calculator - Deterministic cost calculation engine
Executes service-specific cost formulas with full tracing
"""

from typing import List, Dict, Any
from decimal import Decimal
from dataclasses import dataclass, field
import structlog

from services.graph_engine import InfrastructureGraph
from services.plugin_loader import PluginLoader
from models.schemas import ServiceNode, CostBreakdown

logger = structlog.get_logger()


@dataclass
class CostResult:
    """Result of cost calculation for a single node"""
    node_id: str
    service_type: str
    total_monthly_cost: Decimal
    breakdown: Dict[str, Decimal]
    assumptions: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class EstimateResult:
    """Complete cost estimate result"""
    total_monthly_cost: Decimal
    breakdown: List[CostBreakdown]
    warnings: List[str]
    assumptions: List[str]
    confidence: Decimal
    node_costs: Dict[str, CostResult] = field(default_factory=dict)


class CostCalculator:
    """
    Deterministic cost calculation engine
    """
    
    def __init__(self):
        self.logger = logger.bind(component="cost_calculator")
        self.plugin_loader = PluginLoader()
        
        # Initialize pricing loader
        from services.pricing_loader import PricingLoader
        self.pricing_loader = PricingLoader()
    
    async def calculate_estimate(
        self,
        graph: InfrastructureGraph
    ) -> EstimateResult:
        """
        Calculate cost estimate for infrastructure graph
        
        Algorithm:
        1. Topologically sort nodes (dependencies first)
        2. For each node, calculate cost using service plugin
        3. Aggregate total costs
        4. Calculate confidence score
        5. Generate breakdown
        """
        self.logger.info("calculating_estimate", node_count=len(graph.nodes))
        
        # Import here to avoid circular dependency
        from services.graph_engine import GraphEngine
        graph_engine = GraphEngine()
        
        # Step 1: Topological sort
        sorted_nodes = graph_engine.topological_sort(graph)
        
        # Step 2: Calculate cost for each node
        node_costs = {}
        for node in sorted_nodes:
            cost_result = await self._calculate_node_cost(node, graph)
            node_costs[node.id] = cost_result
        
        # Step 3: Aggregate costs
        total_cost = sum(
            result.total_monthly_cost 
            for result in node_costs.values()
        )
        
        # Step 4: Calculate confidence
        confidence = self._calculate_confidence(node_costs.values())
        
        # Step 5: Generate breakdown
        breakdown = self._generate_breakdown(graph, node_costs)
        
        # Collect warnings and assumptions
        all_warnings = list(graph.validation_warnings)
        all_assumptions = []
        
        for cost_result in node_costs.values():
            all_warnings.extend(cost_result.warnings)
            all_assumptions.extend(cost_result.assumptions)
        
        self.logger.info(
            "estimate_calculated",
            total_cost=float(total_cost),
            confidence=float(confidence),
            warning_count=len(all_warnings)
        )
        
        return EstimateResult(
            total_monthly_cost=total_cost,
            breakdown=breakdown,
            warnings=all_warnings,
            assumptions=list(set(all_assumptions)),  # Deduplicate
            confidence=confidence,
            node_costs=node_costs
        )
    
    async def _calculate_node_cost(
        self,
        node: ServiceNode,
        graph: InfrastructureGraph
    ) -> CostResult:
        """Calculate cost for a single node"""
        
        # For virtual cost nodes (DATA_TRANSFER_COST, etc.), return zero
        if node.id.endswith("_COST"):
            return CostResult(
                node_id=node.id,
                service_type=node.service_type,
                total_monthly_cost=Decimal("0.00"),
                breakdown={},
                assumptions=[]
            )
        
        # Get service-specific cost calculation
        cost = await self._get_service_cost(node)
        
        return cost
    
    async def _get_service_cost(self, node: ServiceNode) -> CostResult:
        """
        Get cost for a specific service using the formula engine
        """
        service_type = node.service_type
        config = node.config.copy() if node.config else {}
        
        # Try to load service plugin and use formula engine
        try:
            # Load plugin definition
            service_def = await self.plugin_loader.load_service(service_type)
            
            if not service_def:
                self.logger.warning("service_not_found", service_type=service_type)
                return CostResult(
                    node_id=node.id,
                    service_type=service_type,
                    total_monthly_cost=Decimal("0.00"),
                    breakdown={},
                    assumptions=[f"Service plugin not found for {service_type}"],
                    warnings=[f"Service {service_type} plugin not found"]
                )
            
            # Check if cost formula exists
            if not service_def.cost_formula:
                self.logger.warning("no_cost_formula", service_type=service_type)
                return CostResult(
                    node_id=node.id,
                    service_type=service_type,
                    total_monthly_cost=Decimal("0.00"),
                    breakdown={},
                    assumptions=[f"Cost formula not found for {service_type}"],
                    warnings=[f"Service {service_type} has no cost formula"]
                )
            
            # Inject default values from UI schema for missing config values
            if service_def.ui_schema and 'properties' in service_def.ui_schema:
                for prop_name, prop_def in service_def.ui_schema['properties'].items():
                    if prop_name not in config and 'default' in prop_def:
                        config[prop_name] = prop_def['default']
            
            # Load pricing data for service/region
            pricing_data = await self.pricing_loader.get_pricing(
                service_id=service_type,
                region=node.region
            )
            
            # Convert cost_formula dict to YAML string for FormulaEngine
            import yaml
            formula_yaml = yaml.dump(service_def.cost_formula)
            
            # Execute formula with pricing context
            from services.formula_engine import FormulaEngine
            engine = FormulaEngine()
            formula_def = engine.load_formula(formula_yaml)
            result = engine.execute_formula(formula_def, config, pricing=pricing_data)
            
            # Convert to CostResult
            breakdown_dict = {}
            for step_id, step_data in result['breakdown'].items():
                breakdown_dict[step_id] = Decimal(str(step_data['value']))
            
            # Collect assumptions (include pricing metadata if available)
            assumptions = result.get('assumptions', [])
            if pricing_data and '_metadata' in pricing_data:
                metadata = pricing_data['_metadata']
                assumptions.append(
                    f"Pricing: {metadata['version']} (updated {metadata['last_updated']})"
                )
            
            return CostResult(
                node_id=node.id,
                service_type=service_type,
                total_monthly_cost=Decimal(str(result['total_cost'])),
                breakdown=breakdown_dict,
                assumptions=assumptions,
                warnings=[]
            )
            
        except Exception as e:
            self.logger.error("cost_calculation_error", service_type=service_type, error=str(e))
            return CostResult(
                node_id=node.id,
                service_type=service_type,
                total_monthly_cost=Decimal("0.00"),
                breakdown={},
                assumptions=[f"Error calculating cost for {service_type}"],
                warnings=[f"Cost calculation failed: {str(e)}"]
            )
    
    async def _calculate_ec2_cost(self, node: ServiceNode) -> CostResult:
        """Calculate EC2 instance cost"""
        config = node.config
        
        # Simplified pricing (us-east-1)
        instance_pricing = {
            "t3.micro": Decimal("0.0104"),
            "t3.small": Decimal("0.0208"),
            "t3.medium": Decimal("0.0416"),
            "t3.large": Decimal("0.0832"),
            "m5.large": Decimal("0.096"),
            "m5.xlarge": Decimal("0.192"),
            "m5.2xlarge": Decimal("0.384"),
        }
        
        instance_type = config.get("instance_type", "t3.medium")
        instance_count = config.get("instance_count", 1)
        hours_per_month = 730
        
        # Base instance cost
        hourly_rate = instance_pricing.get(instance_type, Decimal("0.096"))
        instance_cost = hourly_rate * hours_per_month * instance_count
        
        # EBS cost
        ebs_volumes = config.get("ebs_volumes", [])
        ebs_cost = Decimal("0.00")
        for volume in ebs_volumes:
            size_gb = volume.get("size_gb", 100)
            volume_type = volume.get("volume_type", "gp3")
            # gp3: $0.08/GB-month
            ebs_cost += Decimal(str(size_gb)) * Decimal("0.08")
        
        # Data transfer (estimated)
        egress_gb = config.get("estimated_monthly_egress_gb", 100)
        # First 100GB free, then $0.09/GB
        data_transfer_cost = max(Decimal("0"), (Decimal(str(egress_gb)) - 100) * Decimal("0.09"))
        
        total_cost = instance_cost + ebs_cost + data_transfer_cost
        
        return CostResult(
            node_id=node.id,
            service_type="AmazonEC2",
            total_monthly_cost=total_cost,
            breakdown={
                "instance": instance_cost,
                "ebs_storage": ebs_cost,
                "data_transfer": data_transfer_cost
            },
            assumptions=[
                "730 hours per month (24/7 operation)",
                "On-demand pricing (no Reserved Instances)",
                f"Data transfer estimated at {egress_gb}GB/month"
            ]
        )
    
    async def _calculate_lambda_cost(self, node: ServiceNode) -> CostResult:
        """Calculate Lambda function cost"""
        config = node.config
        
        memory_mb = config.get("memory_mb", 512)
        monthly_invocations = config.get("monthly_invocations", 1000000)
        avg_duration_ms = config.get("avg_duration_ms", 200)
        
        # GB-seconds
        gb_seconds = (memory_mb / 1024) * (avg_duration_ms / 1000) * monthly_invocations
        
        # Free tier: 400,000 GB-seconds, 1M requests
        billable_gb_seconds = max(0, gb_seconds - 400000)
        billable_requests = max(0, monthly_invocations - 1000000)
        
        # Pricing: $0.0000166667 per GB-second, $0.20 per 1M requests
        compute_cost = Decimal(str(billable_gb_seconds)) * Decimal("0.0000166667")
        request_cost = Decimal(str(billable_requests / 1000000)) * Decimal("0.20")
        
        total_cost = compute_cost + request_cost
        
        return CostResult(
            node_id=node.id,
            service_type="AWSLambda",
            total_monthly_cost=total_cost,
            breakdown={
                "compute": compute_cost,
                "requests": request_cost
            },
            assumptions=[
                f"Average duration: {avg_duration_ms}ms",
                "No provisioned concurrency",
                "x86_64 architecture"
            ]
        )
    
    async def _calculate_rds_cost(self, node: ServiceNode) -> CostResult:
        """Calculate RDS database cost"""
        config = node.config
        
        # Simplified pricing
        instance_pricing = {
            "db.t3.micro": Decimal("0.017"),
            "db.t3.small": Decimal("0.034"),
            "db.t3.medium": Decimal("0.068"),
            "db.t3.large": Decimal("0.136"),
            "db.r5.large": Decimal("0.24"),
            "db.r5.xlarge": Decimal("0.48"),
        }
        
        instance_class = config.get("instance_class", "db.t3.medium")
        multi_az = config.get("multi_az", False)
        storage_gb = config.get("storage_gb", 100)
        
        # Instance cost
        hourly_rate = instance_pricing.get(instance_class, Decimal("0.068"))
        instance_cost = hourly_rate * 730
        
        # Multi-AZ doubles instance cost
        if multi_az:
            instance_cost *= 2
        
        # Storage cost (gp3: $0.115/GB-month)
        storage_cost = Decimal(str(storage_gb)) * Decimal("0.115")
        if multi_az:
            storage_cost *= 2
        
        # Backup storage (estimated at 100% of DB size)
        backup_cost = Decimal(str(storage_gb)) * Decimal("0.095")
        
        total_cost = instance_cost + storage_cost + backup_cost
        
        return CostResult(
            node_id=node.id,
            service_type="AmazonRDS",
            total_monthly_cost=total_cost,
            breakdown={
                "instance": instance_cost,
                "storage": storage_cost,
                "backup": backup_cost
            },
            assumptions=[
                "730 hours per month (24/7 operation)",
                "On-demand pricing",
                f"Multi-AZ: {multi_az}",
                "Backup storage equals DB size"
            ]
        )
    
    async def _calculate_s3_cost(self, node: ServiceNode) -> CostResult:
        """Calculate S3 storage cost"""
        config = node.config
        
        storage_gb = config.get("storage_gb", 100)
        storage_class = config.get("storage_class", "STANDARD")
        
        # Storage pricing
        storage_pricing = {
            "STANDARD": Decimal("0.023"),
            "INTELLIGENT_TIERING": Decimal("0.023"),
            "STANDARD_IA": Decimal("0.0125"),
            "GLACIER": Decimal("0.004"),
        }
        
        storage_rate = storage_pricing.get(storage_class, Decimal("0.023"))
        storage_cost = Decimal(str(storage_gb)) * storage_rate
        
        # Request costs (simplified)
        monthly_put_requests = config.get("monthly_put_requests", 10000)
        monthly_get_requests = config.get("monthly_get_requests", 100000)
        
        put_cost = Decimal(str(monthly_put_requests / 1000)) * Decimal("0.005")
        get_cost = Decimal(str(monthly_get_requests / 1000)) * Decimal("0.0004")
        
        total_cost = storage_cost + put_cost + get_cost
        
        return CostResult(
            node_id=node.id,
            service_type="AmazonS3",
            total_monthly_cost=total_cost,
            breakdown={
                "storage": storage_cost,
                "put_requests": put_cost,
                "get_requests": get_cost
            },
            assumptions=[
                f"Storage class: {storage_class}",
                "Data transfer costs not included (use CloudFront)"
            ]
        )
    
    def _calculate_confidence(self, cost_results: List[CostResult]) -> Decimal:
        """
        Calculate overall confidence score (0.0 to 1.0)
        Reduced by estimations and assumptions
        """
        base_confidence = Decimal("1.0")
        
        # Reduce confidence for each assumption
        assumption_count = sum(len(r.assumptions) for r in cost_results)
        confidence_reduction = min(Decimal("0.30"), Decimal(str(assumption_count)) * Decimal("0.05"))
        
        return max(Decimal("0.50"), base_confidence - confidence_reduction)
    
    def _generate_breakdown(
        self,
        graph: InfrastructureGraph,
        node_costs: Dict[str, CostResult]
    ) -> List[CostBreakdown]:
        """Generate cost breakdown by service, region, category"""
        breakdowns = []
        
        # By service
        for node_id, cost_result in node_costs.items():
            if node_id in graph.nodes:
                # Convert Decimal breakdown values to float
                details_float = {}
                if cost_result.breakdown:
                    details_float = {k: float(v) for k, v in cost_result.breakdown.items()}
                
                breakdowns.append(CostBreakdown(
                    dimension="service",
                    key=cost_result.service_type,
                    value=float(cost_result.total_monthly_cost),  # Convert Decimal to float
                    details=details_float if details_float else None
                ))
        
        # By region
        region_costs = {}
        for node_id, cost_result in node_costs.items():
            if node_id in graph.nodes:
                node = graph.nodes[node_id]
                region = node.region
                region_costs[region] = region_costs.get(region, Decimal("0")) + cost_result.total_monthly_cost
        
        for region, cost in region_costs.items():
            breakdowns.append(CostBreakdown(
                dimension="region",
                key=region,
                value=float(cost),  # Convert Decimal to float
                details=None
            ))
        
        return breakdowns
