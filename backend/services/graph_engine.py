"""
Graph Engine - DAG-based dependency resolution
Builds infrastructure graphs with implicit dependency injection
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import networkx as nx
import structlog

from models.schemas import ServiceNode, DependencyEdge

logger = structlog.get_logger()


class DependencyType(Enum):
    """Types of dependencies between services"""
    MANDATORY = "mandatory"
    CONDITIONAL = "conditional"
    IMPLICIT = "implicit"
    COST_ONLY = "cost_only"


@dataclass
class InfrastructureGraph:
    """Complete infrastructure graph with nodes and edges"""
    nodes: Dict[str, ServiceNode]
    edges: List[DependencyEdge]
    graph: nx.DiGraph
    meta_data: Dict[str, Any] = field(default_factory=dict)
    validation_errors: List[str] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)


class GraphEngine:
    """
    Core engine for building and validating infrastructure graphs
    """
    
    def __init__(self):
        self.logger = logger.bind(component="graph_engine")
    
    async def build_graph(
        self,
        services: List[ServiceNode],
        explicit_edges: List[DependencyEdge] = None
    ) -> InfrastructureGraph:
        """
        Build infrastructure graph from user-defined services
        
        Algorithm:
        1. Create nodes from services
        2. Add explicit dependencies
        3. Inject implicit dependencies
        4. Build NetworkX DiGraph
        5. Validate graph
        6. Return validated graph
        """
        self.logger.info("building_graph", service_count=len(services))
        
        # Step 1: Create nodes
        nodes = {service.id: service for service in services}
        
        # Step 2: Add explicit dependencies
        edges = explicit_edges or []
        
        # Step 3: Inject implicit dependencies
        implicit_edges = await self._inject_implicit_dependencies(nodes, edges)
        all_edges = edges + implicit_edges
        
        # Step 4: Build NetworkX graph
        graph = nx.DiGraph()
        graph.add_nodes_from(nodes.keys())
        for edge in all_edges:
            graph.add_edge(edge.source, edge.target, edge_data=edge)
        
        # Step 5: Validate graph
        infra_graph = InfrastructureGraph(
            nodes=nodes,
            edges=all_edges,
            graph=graph
        )
        
        await self._validate_graph(infra_graph)
        
        self.logger.info(
            "graph_built",
            node_count=len(nodes),
            edge_count=len(all_edges),
            implicit_edge_count=len(implicit_edges)
        )
        
        return infra_graph
    
    async def _inject_implicit_dependencies(
        self,
        nodes: Dict[str, ServiceNode],
        existing_edges: List[DependencyEdge]
    ) -> List[DependencyEdge]:
        """
        Inject implicit dependencies based on service configurations
        
        Examples:
        - EC2 in private subnet + internet access → NAT Gateway
        - EC2 without CloudFront → Data Transfer costs
        - RDS Multi-AZ → Cross-AZ traffic costs
        """
        implicit_edges = []
        
        for node in nodes.values():
            # EC2 implicit dependencies
            if node.service_type == "AmazonEC2":
                # NAT Gateway for private subnet with internet access
                if (node.config.get("subnet_type") == "private" and 
                    node.config.get("internet_access", True)):
                    implicit_edges.append(DependencyEdge(
                        source=node.id,
                        target="NAT_GATEWAY_COST",
                        type=DependencyType.IMPLICIT.value,
                        reason="NAT Gateway required for internet access from private subnet",
                        cost_impact={
                            "driver": "nat_gateway_data_processing",
                            "estimated_range": [10, 500]
                        }
                    ))
                
                # Data transfer costs if no CloudFront
                has_cloudfront = any(
                    n.service_type == "AmazonCloudFront" 
                    for n in nodes.values()
                )
                if not has_cloudfront:
                    implicit_edges.append(DependencyEdge(
                        source=node.id,
                        target="DATA_TRANSFER_COST",
                        type=DependencyType.COST_ONLY.value,
                        reason="Data transfer out charges apply",
                        cost_impact={
                            "driver": "ec2_data_transfer_out",
                            "estimated_range": [5, 1000]
                        }
                    ))
            
            # Lambda implicit dependencies
            elif node.service_type == "AWSLambda":
                # CloudWatch Logs (always)
                implicit_edges.append(DependencyEdge(
                    source=node.id,
                    target="CLOUDWATCH_LOGS_COST",
                    type=DependencyType.IMPLICIT.value,
                    reason="Lambda automatically logs to CloudWatch",
                    cost_impact={
                        "driver": "lambda_logs",
                        "estimated_range": [1, 50]
                    }
                ))
            
            # RDS implicit dependencies
            elif node.service_type == "AmazonRDS":
                # Multi-AZ replication traffic
                if node.config.get("multi_az", False):
                    implicit_edges.append(DependencyEdge(
                        source=node.id,
                        target="CROSS_AZ_TRAFFIC_COST",
                        type=DependencyType.IMPLICIT.value,
                        reason="Multi-AZ synchronous replication traffic",
                        cost_impact={
                            "driver": "rds_multi_az_replication",
                            "estimated_range": [10, 200]
                        }
                    ))
        
        return implicit_edges
    
    async def _validate_graph(self, graph: InfrastructureGraph) -> None:
        """
        Validate infrastructure graph
        
        Checks:
        1. No cycles (DAG requirement)
        2. No orphaned nodes
        3. Cross-region dependencies flagged
        """
        # Check for cycles
        if not nx.is_directed_acyclic_graph(graph.graph):
            cycles = list(nx.simple_cycles(graph.graph))
            graph.validation_errors.append(
                f"Graph contains {len(cycles)} cycle(s): {cycles}"
            )
            self.logger.error("graph_validation_failed", reason="cycles_detected", cycles=cycles)
        
        # Check for orphaned nodes
        orphans = [
            node_id for node_id in graph.nodes.keys()
            if graph.graph.degree(node_id) == 0
        ]
        if orphans:
            graph.validation_warnings.append(
                f"Found {len(orphans)} orphaned node(s): {orphans}"
            )
        
        # Check cross-region dependencies
        cross_region_edges = [
            edge for edge in graph.edges
            if (edge.source in graph.nodes and 
                edge.target in graph.nodes and
                graph.nodes[edge.source].region != graph.nodes[edge.target].region)
        ]
        if cross_region_edges:
            graph.validation_warnings.append(
                f"Found {len(cross_region_edges)} cross-region dependencies. "
                f"This may incur data transfer costs."
            )
        
        self.logger.info(
            "graph_validated",
            error_count=len(graph.validation_errors),
            warning_count=len(graph.validation_warnings)
        )
    
    def topological_sort(self, graph: InfrastructureGraph) -> List[ServiceNode]:
        """
        Topologically sort nodes for dependency-order processing
        Dependencies must be processed before dependents
        """
        try:
            sorted_ids = list(nx.topological_sort(graph.graph))
            return [graph.nodes[node_id] for node_id in sorted_ids if node_id in graph.nodes]
        except nx.NetworkXError as e:
            self.logger.error("topological_sort_failed", error=str(e))
            raise ValueError("Graph contains cycles, cannot perform topological sort") from e
