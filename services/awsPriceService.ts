import { PricingClient, GetProductsCommand } from "@aws-sdk/client-pricing";
import { EC2Client, DescribeSpotPriceHistoryCommand } from "@aws-sdk/client-ec2";
import { InfrastructureResource, CostEstimationResult, CostItem } from "../types";

export interface AwsCredentials {
  accessKeyId: string;
  secretAccessKey: string;
  region: string;
}

const REGION_MAP: Record<string, string> = {
  'us-east-1': 'US East (N. Virginia)',
  'us-west-2': 'US West (Oregon)',
  'eu-central-1': 'EU (Frankfurt)',
  'ap-southeast-1': 'Asia Pacific (Singapore)',
};

export const estimateInfrastructureCost = async (
  resources: InfrastructureResource[],
  credentials: AwsCredentials
): Promise<CostEstimationResult> => {
  if (!resources || resources.length === 0) {
    throw new Error("No resources to estimate.");
  }

  const pricingClient = new PricingClient({
    region: 'us-east-1', // Pricing API is only available in us-east-1 and ap-south-1
    credentials: {
      accessKeyId: credentials.accessKeyId,
      secretAccessKey: credentials.secretAccessKey,
    },
  });

  const ec2Client = new EC2Client({
    region: credentials.region || 'us-east-1',
    credentials: {
      accessKeyId: credentials.accessKeyId,
      secretAccessKey: credentials.secretAccessKey,
    }
  });

  const breakdown: CostItem[] = [];
  let totalMonthlyCost = 0;

  for (const resource of resources) {
    let cost = 0;
    let explanation = "";

    try {
      switch (resource.serviceId) {
        case 'ec2':
          const ec2Cost = await calculateEc2Cost(pricingClient, ec2Client, resource.config);
          cost = ec2Cost.cost;
          explanation = ec2Cost.explanation;
          break;
        case 's3':
          const s3Cost = calculateS3Cost(resource.config);
          cost = s3Cost.cost;
          explanation = s3Cost.explanation;
          break;
        default:
          explanation = "Cost estimation not yet implemented for this service via API.";
          break;
      }
    } catch (error) {
      console.error(`Error calculating cost for ${resource.serviceName}:`, error);
      explanation = "Error retrieving price from AWS.";
    }

    breakdown.push({
      resourceName: `${resource.serviceName} (${resource.id.substring(0, 4)})`,
      monthlyCost: cost,
      explanation: explanation,
    });
    totalMonthlyCost += cost;
  }

  return {
    totalMonthlyCost,
    currency: "USD",
    summary: `Estimated monthly cost based on AWS Price List API & Spot Pricing.`,
    breakdown,
  };
};

async function calculateEc2Cost(pricingClient: PricingClient, ec2Client: EC2Client, config: any): Promise<{ cost: number; explanation: string }> {
  const instanceType = config.instanceType;
  const region = config.region || 'us-east-1';
  const os = config.os || 'Linux';
  const purchaseOption = config.purchaseOption || 'On-Demand';
  const location = REGION_MAP[region];

  if (purchaseOption === 'Spot') {
    try {
      const command = new DescribeSpotPriceHistoryCommand({
        InstanceTypes: [instanceType],
        ProductDescriptions: [os === 'Linux' ? 'Linux/UNIX' : 'Windows'],
        MaxResults: 1,
        StartTime: new Date() // Current price
      });
      const response = await ec2Client.send(command);
      if (response.SpotPriceHistory && response.SpotPriceHistory.length > 0) {
        const spotPrice = parseFloat(response.SpotPriceHistory[0].SpotPrice || "0");
        return {
          cost: spotPrice * 730,
          explanation: `$${spotPrice} (Spot) * 730 hrs`
        };
      }
    } catch (e) {
      console.warn("Failed to fetch Spot price, falling back to On-Demand", e);
      // Fallback to On-Demand
    }
  }

  if (!location) {
    return { cost: 0, explanation: `Region ${region} not supported for pricing lookup yet.` };
  }

  const command = new GetProductsCommand({
    ServiceCode: 'AmazonEC2',
    Filters: [
      { Type: 'TERM_MATCH', Field: 'instanceType', Value: instanceType },
      { Type: 'TERM_MATCH', Field: 'location', Value: location },
      { Type: 'TERM_MATCH', Field: 'operatingSystem', Value: os },
      { Type: 'TERM_MATCH', Field: 'preInstalledSw', Value: 'NA' },
      { Type: 'TERM_MATCH', Field: 'tenancy', Value: config.tenancy || 'Shared' },
      { Type: 'TERM_MATCH', Field: 'capacitystatus', Value: 'Used' },
    ],
    MaxResults: 1
  });

  try {
    const response = await pricingClient.send(command);

    if (response.PriceList && response.PriceList.length > 0) {
      const priceItemStr = response.PriceList[0] as string;
      const priceItem = JSON.parse(priceItemStr);

      const terms = priceItem.terms?.OnDemand;
      if (terms) {
        const termId = Object.keys(terms)[0];
        const priceDimensions = terms[termId].priceDimensions;
        const priceDimensionId = Object.keys(priceDimensions)[0];
        const pricePerUnit = priceDimensions[priceDimensionId].pricePerUnit.USD;

        const hourlyPrice = parseFloat(pricePerUnit);
        const monthlyPrice = hourlyPrice * 730;

        return {
          cost: monthlyPrice,
          explanation: `$${hourlyPrice.toFixed(4)}/hr * 730 hrs (On-Demand)`
        };
      }
    }
    return { cost: 0, explanation: "Pricing data not found for this configuration." };
  } catch (e) {
    console.error("AWS Pricing API Error", e);
    throw e;
  }
}

function calculateS3Cost(config: any): { cost: number; explanation: string } {
  const capacity = Number(config.capacity) || 0;
  const isVersioning = config.versioning === 'Enabled';
  const isReplication = config.replication !== 'None';

  // Base cost (Standard) - simplified
  let cost = capacity * 0.023;
  let explanationParts = [`$0.023 * ${capacity} GB`];

  if (isVersioning) {
    // Assumption: Versioning adds 50% overhead on average for active buckets
    const versioningCost = cost * 0.5;
    cost += versioningCost;
    explanationParts.push(`+ $${versioningCost.toFixed(2)} (Versioning Est.)`);
  }

  if (isReplication) {
    // Replication: Storage cost in dest + Transfer cost
    // Simplified: Double storage cost + $0.02/GB transfer
    const replicationStorage = capacity * 0.023;
    const transferCost = capacity * 0.02;
    cost += replicationStorage + transferCost;
    explanationParts.push(`+ $${(replicationStorage + transferCost).toFixed(2)} (Replication & Transfer)`);
  }

  return {
    cost,
    explanation: explanationParts.join(' ')
  };
}
