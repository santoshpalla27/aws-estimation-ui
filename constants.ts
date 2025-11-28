import { ServiceDefinition } from './types';

export const AWS_SERVICES: ServiceDefinition[] = [
  {
    id: 'ec2',
    name: 'EC2 Instance',
    description: 'Virtual servers in the cloud',
    icon: 'Server',
    fields: [
      { key: 'region', label: 'Region', type: 'select', category: 'Basic', options: ['us-east-1', 'us-west-2', 'eu-central-1', 'ap-southeast-1'], defaultValue: 'us-east-1' },
      { key: 'instanceType', label: 'Instance Type', type: 'select', category: 'Compute', options: ['t3.micro', 't3.medium', 't4g.medium', 'm5.large', 'm5.xlarge', 'm6g.large', 'c5.large', 'c5.xlarge', 'c6g.large', 'r5.large', 'g4dn.xlarge'], defaultValue: 't3.medium' },
      { key: 'os', label: 'Operating System', type: 'select', category: 'Compute', options: ['Linux', 'Windows', 'RHEL', 'SUSE'], defaultValue: 'Linux' },
      { key: 'tenancy', label: 'Tenancy', type: 'select', category: 'Advanced', options: ['Shared', 'Dedicated'], defaultValue: 'Shared', optional: true },
      { key: 'purchaseOption', label: 'Payment Model', type: 'select', category: 'Basic', options: ['On-Demand', 'Spot', 'Savings Plan (1yr)', 'Savings Plan (3yr)'], defaultValue: 'On-Demand' },

      { key: 'ebsType', label: 'Root Volume Type', type: 'select', category: 'Storage', options: ['gp3', 'gp2', 'io2', 'st1'], defaultValue: 'gp3' },
      { key: 'storage', label: 'Storage Size', type: 'number', category: 'Storage', unit: 'GB', placeholder: '30', defaultValue: 30 },
      { key: 'iops', label: 'Provisioned IOPS', type: 'number', category: 'Storage', unit: 'IOPS', placeholder: '3000', optional: true, tooltip: 'Only for gp3/io2 volumes' },

      { key: 'dataTransferOut', label: 'Data Transfer Out (Internet)', type: 'number', category: 'Network', unit: 'GB/mo', placeholder: '10' },
      { key: 'elasticIp', label: 'Unattached Elastic IP Hours', type: 'number', category: 'Network', unit: 'Hours', optional: true, placeholder: '0' },
    ],
  },
  {
    id: 'rds',
    name: 'RDS Database',
    description: 'Managed Relational Database Service',
    icon: 'Database',
    fields: [
      { key: 'engine', label: 'Engine', type: 'select', category: 'Basic', options: ['PostgreSQL', 'MySQL', 'Aurora PostgreSQL', 'Aurora MySQL', 'MariaDB', 'SQL Server Std'], defaultValue: 'PostgreSQL' },
      { key: 'class', label: 'Instance Class', type: 'select', category: 'Compute', options: ['db.t3.micro', 'db.t3.medium', 'db.m5.large', 'db.r5.xlarge', 'db.r6g.large'], defaultValue: 'db.t3.medium' },
      { key: 'multiAz', label: 'Deployment Option', type: 'select', category: 'Advanced', options: ['Single AZ', 'Multi-AZ Standby', 'Multi-AZ Cluster'], defaultValue: 'Single AZ' },

      { key: 'storageType', label: 'Storage Type', type: 'select', category: 'Storage', options: ['gp3', 'gp2', 'io1', 'aurora-standard'], defaultValue: 'gp3' },
      { key: 'storage', label: 'Allocated Storage', type: 'number', category: 'Storage', unit: 'GB', placeholder: '100', defaultValue: 100 },
      { key: 'backupStorage', label: 'Addt. Backup Storage', type: 'number', category: 'Storage', unit: 'GB', optional: true, placeholder: '50' },
    ],
  },
  {
    id: 's3',
    name: 'S3 Storage',
    description: 'Scalable object storage',
    icon: 'HardDrive',
    fields: [
      { key: 'class', label: 'Storage Class', type: 'select', category: 'Basic', options: ['Standard', 'Intelligent-Tiering', 'Standard-IA', 'Glacier Instant Retrieval'], defaultValue: 'Standard' },
      { key: 'capacity', label: 'Total Storage', type: 'number', category: 'Storage', unit: 'GB', placeholder: '1000' },
      { key: 'versioning', label: 'Versioning Enabled', type: 'select', category: 'Features', options: ['Enabled', 'Disabled'], defaultValue: 'Disabled', tooltip: 'May double storage costs if frequent overwrites occur' },
      { key: 'replication', label: 'Cross-Region Replication', type: 'select', category: 'Features', options: ['None', 'US East (N. Virginia)', 'US West (Oregon)', 'EU (Frankfurt)'], defaultValue: 'None' },

      { key: 'requestsTier1', label: 'PUT/COPY/POST Requests', type: 'number', category: 'Advanced', unit: 'Thousands', placeholder: '10' },
      { key: 'requestsTier2', label: 'GET/SELECT Requests', type: 'number', category: 'Advanced', unit: 'Thousands', placeholder: '100' },
      { key: 'transferOut', label: 'Data Transfer Out', type: 'number', category: 'Network', unit: 'GB', placeholder: '50' },
    ],
  },
  {
    id: 'lambda',
    name: 'Lambda',
    description: 'Serverless compute',
    icon: 'Layers',
    fields: [
      { key: 'architecture', label: 'Architecture', type: 'select', category: 'Basic', options: ['x86', 'Arm64 (Graviton)'], defaultValue: 'x86' },
      { key: 'invocations', label: 'Monthly Requests', type: 'number', category: 'Compute', unit: 'Millions', placeholder: '1' },
      { key: 'duration', label: 'Avg Duration', type: 'number', category: 'Compute', unit: 'ms', placeholder: '300' },
      { key: 'memory', label: 'Memory Allocated', type: 'number', category: 'Compute', unit: 'MB', placeholder: '128', defaultValue: 128 },
      { key: 'ephemeralStorage', label: 'Ephemeral Storage', type: 'number', category: 'Storage', unit: 'MB', defaultValue: 512 },
    ],
  },
  {
    id: 'vpc',
    name: 'VPC & Networking',
    description: 'Virtual Private Cloud resources',
    icon: 'Router',
    fields: [
      { key: 'natGateways', label: 'NAT Gateways Count', type: 'number', category: 'Network', unit: 'Count', placeholder: '0', tooltip: 'Hourly charge applies per GW' },
      { key: 'natData', label: 'NAT Data Processed', type: 'number', category: 'Network', unit: 'GB', placeholder: '0' },
      { key: 'publicIps', label: 'Public IPv4 Addresses', type: 'number', category: 'Network', unit: 'Count', placeholder: '1', tooltip: '$0.005/hr per IP' },
      { key: 'vpcEndpoints', label: 'Interface Endpoints', type: 'number', category: 'Advanced', unit: 'Count', placeholder: '0' },
      { key: 'vpnConnections', label: 'Site-to-Site VPNs', type: 'number', category: 'Advanced', unit: 'Count', placeholder: '0' },
    ],
  },
  {
    id: 'elb',
    name: 'Elastic Load Balancer',
    description: 'Distribute incoming traffic',
    icon: 'Network',
    fields: [
      { key: 'type', label: 'Type', type: 'select', category: 'Basic', options: ['Application Load Balancer', 'Network Load Balancer', 'Gateway Load Balancer'], defaultValue: 'Application Load Balancer' },
      { key: 'count', label: 'Number of LBs', type: 'number', category: 'Basic', unit: 'Count', defaultValue: 1 },
      { key: 'processedBytes', label: 'Data Processed', type: 'number', category: 'Network', unit: 'GB', placeholder: '100' },
      { key: 'newConnections', label: 'New Connections/sec', type: 'number', category: 'Advanced', unit: 'Count', placeholder: '10', optional: true },
    ],
  },
  {
    id: 'dynamodb',
    name: 'DynamoDB',
    description: 'NoSQL Database',
    icon: 'Database',
    fields: [
      { key: 'capacityMode', label: 'Capacity Mode', type: 'select', category: 'Basic', options: ['On-Demand', 'Provisioned'], defaultValue: 'On-Demand' },
      { key: 'storage', label: 'Data Storage', type: 'number', category: 'Storage', unit: 'GB', placeholder: '10' },
      { key: 'wcu', label: 'Write Capacity / Units', type: 'number', category: 'Compute', unit: 'Units/mo', placeholder: '1000000', tooltip: 'Writes per month (On-Demand) or WCU (Provisioned)' },
      { key: 'rcu', label: 'Read Capacity / Units', type: 'number', category: 'Compute', unit: 'Units/mo', placeholder: '5000000' },
      { key: 'backup', label: 'Point-in-time Recovery', type: 'select', category: 'Features', options: ['Enabled', 'Disabled'], defaultValue: 'Disabled' },
    ],
  },
  {
    id: 'eks',
    name: 'EKS Cluster',
    description: 'Kubernetes Control Plane',
    icon: 'Server',
    fields: [
      { key: 'clusters', label: 'Number of Clusters', type: 'number', category: 'Basic', unit: 'Count', defaultValue: 1, tooltip: '$0.10 per hour per cluster' },
      { key: 'fargateVCpu', label: 'Fargate vCPU Hours', type: 'number', category: 'Compute', unit: 'Hours', optional: true },
      { key: 'fargateMemory', label: 'Fargate Memory Hours', type: 'number', category: 'Compute', unit: 'GB-Hours', optional: true },
    ],
  },
  {
    id: 'cloudfront',
    name: 'CloudFront CDN',
    description: 'Content Delivery Network',
    icon: 'Globe',
    fields: [
      { key: 'transferOut', label: 'Data Transfer Out', type: 'number', category: 'Network', unit: 'GB', placeholder: '500' },
      { key: 'requests', label: 'Total Requests', type: 'number', category: 'Network', unit: 'Millions', placeholder: '10' },
      { key: 'zone', label: 'Price Class', type: 'select', category: 'Advanced', options: ['All Edge Locations', 'North America & Europe Only'], defaultValue: 'All Edge Locations' },
    ],
  },
  {
    id: 'waf',
    name: 'WAF',
    description: 'Web Application Firewall',
    icon: 'Shield',
    fields: [
      { key: 'acls', label: 'Web ACLs', type: 'number', category: 'Basic', unit: 'Count', placeholder: '1' },
      { key: 'rules', label: 'Rules per ACL', type: 'number', category: 'Basic', unit: 'Count', placeholder: '5' },
      { key: 'requests', label: 'Requests Scanned', type: 'number', category: 'Network', unit: 'Millions', placeholder: '2' },
    ],
  },
  {
    id: 'cloudwatch',
    name: 'CloudWatch',
    description: 'Monitoring and observability',
    icon: 'Activity',
    fields: [
      { key: 'logsIngested', label: 'Logs Ingested', type: 'number', category: 'Storage', unit: 'GB', placeholder: '10' },
      { key: 'metrics', label: 'Custom Metrics', type: 'number', category: 'Advanced', unit: 'Count', placeholder: '10' },
      { key: 'dashboards', label: 'Dashboards', type: 'number', category: 'Advanced', unit: 'Count', placeholder: '1' },
      { key: 'alarms', label: 'Alarms', type: 'number', category: 'Advanced', unit: 'Count', placeholder: '5' },
    ],
  },
  {
    id: 'secretsmanager',
    name: 'Secrets Manager',
    description: 'Rotate, manage, and retrieve secrets',
    icon: 'Key',
    fields: [
      { key: 'secrets', label: 'Number of Secrets', type: 'number', category: 'Basic', unit: 'Count', placeholder: '5' },
      { key: 'apiCalls', label: 'API Calls', type: 'number', category: 'Compute', unit: 'Thousands', placeholder: '50' },
    ],
  },
  {
    id: 'route53',
    name: 'Route 53',
    description: 'DNS web service',
    icon: 'Globe',
    fields: [
      { key: 'zones', label: 'Hosted Zones', type: 'number', category: 'Basic', unit: 'Count', placeholder: '1' },
      { key: 'queries', label: 'Standard Queries', type: 'number', category: 'Network', unit: 'Millions', placeholder: '5' },
      { key: 'checks', label: 'Health Checks', type: 'number', category: 'Advanced', unit: 'Count', optional: true },
    ],
  },
  {
    id: 'apigateway',
    name: 'API Gateway',
    description: 'Create and manage APIs',
    icon: 'Zap',
    fields: [
      { key: 'type', label: 'API Type', type: 'select', category: 'Basic', options: ['REST API', 'HTTP API', 'WebSocket'], defaultValue: 'REST API' },
      { key: 'requests', label: 'Requests', type: 'number', category: 'Network', unit: 'Millions', placeholder: '5' },
      { key: 'cache', label: 'Cache Capacity', type: 'select', category: 'Features', options: ['None', '0.5 GB', '1.6 GB', '6.1 GB', '13.5 GB'], defaultValue: 'None' },
    ],
  },
];
