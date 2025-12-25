-- Service-specific pricing tables for deterministic SKU matching

-- EC2 Pricing
CREATE TABLE IF NOT EXISTS pricing_ec2 (
    id SERIAL PRIMARY KEY,
    version_id INTEGER NOT NULL REFERENCES pricing_versions(id) ON DELETE CASCADE,
    sku VARCHAR(255) NOT NULL,
    
    -- Required attributes for EC2
    instance_type VARCHAR(50) NOT NULL,
    operating_system VARCHAR(50) NOT NULL,
    tenancy VARCHAR(20) NOT NULL,
    capacity_status VARCHAR(20),
    pre_installed_sw VARCHAR(50),
    
    -- Location
    region VARCHAR(50) NOT NULL,
    
    -- Pricing
    price_per_unit DECIMAL(20, 10) NOT NULL,
    unit VARCHAR(50) NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint for deterministic matching
    UNIQUE(version_id, instance_type, operating_system, tenancy, region, capacity_status)
);

CREATE INDEX idx_pricing_ec2_lookup ON pricing_ec2(version_id, instance_type, region);
CREATE INDEX idx_pricing_ec2_version ON pricing_ec2(version_id);

-- RDS Pricing
CREATE TABLE IF NOT EXISTS pricing_rds (
    id SERIAL PRIMARY KEY,
    version_id INTEGER NOT NULL REFERENCES pricing_versions(id) ON DELETE CASCADE,
    sku VARCHAR(255) NOT NULL,
    
    -- Required attributes for RDS
    instance_class VARCHAR(50) NOT NULL,
    database_engine VARCHAR(50) NOT NULL,
    deployment_option VARCHAR(50) NOT NULL,  -- Single-AZ, Multi-AZ
    database_edition VARCHAR(50),
    license_model VARCHAR(50),
    
    -- Location
    region VARCHAR(50) NOT NULL,
    
    -- Pricing
    price_per_unit DECIMAL(20, 10) NOT NULL,
    unit VARCHAR(50) NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint
    UNIQUE(version_id, instance_class, database_engine, deployment_option, region)
);

CREATE INDEX idx_pricing_rds_lookup ON pricing_rds(version_id, instance_class, region);

-- S3 Pricing
CREATE TABLE IF NOT EXISTS pricing_s3 (
    id SERIAL PRIMARY KEY,
    version_id INTEGER NOT NULL REFERENCES pricing_versions(id) ON DELETE CASCADE,
    sku VARCHAR(255) NOT NULL,
    
    -- Required attributes for S3
    storage_class VARCHAR(50) NOT NULL,
    volume_type VARCHAR(50),  -- Storage, Requests, Data Transfer
    
    -- Location
    region VARCHAR(50) NOT NULL,
    from_location VARCHAR(50),  -- For data transfer
    to_location VARCHAR(50),
    
    -- Pricing
    price_per_unit DECIMAL(20, 10) NOT NULL,
    unit VARCHAR(50) NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint
    UNIQUE(version_id, storage_class, volume_type, region)
);

CREATE INDEX idx_pricing_s3_lookup ON pricing_s3(version_id, storage_class, region);

-- EBS Pricing
CREATE TABLE IF NOT EXISTS pricing_ebs (
    id SERIAL PRIMARY KEY,
    version_id INTEGER NOT NULL REFERENCES pricing_versions(id) ON DELETE CASCADE,
    sku VARCHAR(255) NOT NULL,
    
    -- Required attributes for EBS
    volume_type VARCHAR(50) NOT NULL,  -- gp2, gp3, io1, io2, st1, sc1
    
    -- Location
    region VARCHAR(50) NOT NULL,
    
    -- Pricing
    price_per_unit DECIMAL(20, 10) NOT NULL,
    unit VARCHAR(50) NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint
    UNIQUE(version_id, volume_type, region)
);

CREATE INDEX idx_pricing_ebs_lookup ON pricing_ebs(version_id, volume_type, region);

-- Lambda Pricing
CREATE TABLE IF NOT EXISTS pricing_lambda (
    id SERIAL PRIMARY KEY,
    version_id INTEGER NOT NULL REFERENCES pricing_versions(id) ON DELETE CASCADE,
    sku VARCHAR(255) NOT NULL,
    
    -- Required attributes for Lambda
    group_description VARCHAR(100) NOT NULL,  -- Requests, Duration, etc.
    
    -- Location
    region VARCHAR(50) NOT NULL,
    
    -- Pricing
    price_per_unit DECIMAL(20, 10) NOT NULL,
    unit VARCHAR(50) NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint
    UNIQUE(version_id, group_description, region)
);

CREATE INDEX idx_pricing_lambda_lookup ON pricing_lambda(version_id, group_description, region);

-- Comments
COMMENT ON TABLE pricing_ec2 IS 'Normalized EC2 instance pricing - one row per billable SKU';
COMMENT ON TABLE pricing_rds IS 'Normalized RDS instance pricing - one row per billable SKU';
COMMENT ON TABLE pricing_s3 IS 'Normalized S3 storage pricing - one row per billable SKU';
COMMENT ON TABLE pricing_ebs IS 'Normalized EBS volume pricing - one row per billable SKU';
COMMENT ON TABLE pricing_lambda IS 'Normalized Lambda pricing - one row per billable SKU';
