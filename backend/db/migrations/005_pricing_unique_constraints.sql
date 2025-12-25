-- Add unique constraints to all pricing tables
-- Ensures deterministic SKU matching - no ambiguity possible

-- EC2: Enforce unique combination of all pricing dimensions
ALTER TABLE pricing_ec2 
DROP CONSTRAINT IF EXISTS uq_pricing_ec2_sku;

ALTER TABLE pricing_ec2
ADD CONSTRAINT uq_pricing_ec2_sku UNIQUE (
    version_id,
    instance_type,
    operating_system,
    tenancy,
    region,
    capacity_status
);

COMMENT ON CONSTRAINT uq_pricing_ec2_sku ON pricing_ec2 IS 
'Ensures deterministic SKU matching - prevents multiple matches for same attributes';

-- RDS: Enforce unique combination
ALTER TABLE pricing_rds
DROP CONSTRAINT IF EXISTS uq_pricing_rds_sku;

ALTER TABLE pricing_rds
ADD CONSTRAINT uq_pricing_rds_sku UNIQUE (
    version_id,
    instance_class,
    engine,
    region,
    deployment_option
);

COMMENT ON CONSTRAINT uq_pricing_rds_sku ON pricing_rds IS 
'Ensures deterministic SKU matching for RDS instances';

-- S3: Enforce unique combination
ALTER TABLE pricing_s3
DROP CONSTRAINT IF EXISTS uq_pricing_s3_sku;

ALTER TABLE pricing_s3
ADD CONSTRAINT uq_pricing_s3_sku UNIQUE (
    version_id,
    storage_class,
    volume_type,
    region
);

COMMENT ON CONSTRAINT uq_pricing_s3_sku ON pricing_s3 IS 
'Ensures deterministic SKU matching for S3 storage';

-- EBS: Enforce unique combination
ALTER TABLE pricing_ebs
DROP CONSTRAINT IF EXISTS uq_pricing_ebs_sku;

ALTER TABLE pricing_ebs
ADD CONSTRAINT uq_pricing_ebs_sku UNIQUE (
    version_id,
    volume_type,
    region
);

COMMENT ON CONSTRAINT uq_pricing_ebs_sku ON pricing_ebs IS 
'Ensures deterministic SKU matching for EBS volumes';

-- Lambda: Enforce unique combination
ALTER TABLE pricing_lambda
DROP CONSTRAINT IF EXISTS uq_pricing_lambda_sku;

ALTER TABLE pricing_lambda
ADD CONSTRAINT uq_pricing_lambda_sku UNIQUE (
    version_id,
    group_description,
    region
);

COMMENT ON CONSTRAINT uq_pricing_lambda_sku ON pricing_lambda IS 
'Ensures deterministic SKU matching for Lambda functions';

-- Verify constraints
DO $$
DECLARE
    constraint_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO constraint_count
    FROM information_schema.table_constraints
    WHERE constraint_type = 'UNIQUE'
      AND table_name IN ('pricing_ec2', 'pricing_rds', 'pricing_s3', 'pricing_ebs', 'pricing_lambda')
      AND constraint_name LIKE 'uq_pricing_%';
    
    IF constraint_count >= 5 THEN
        RAISE NOTICE 'SUCCESS: All % unique constraints created', constraint_count;
    ELSE
        RAISE WARNING 'Only % unique constraints found, expected 5', constraint_count;
    END IF;
END $$;
