-- AWS Terraform Cost Calculator Database Schema
-- Production-ready schema with proper constraints, indexes, and relationships

-- ============================================================================
-- PRICING TABLES
-- ============================================================================

-- Pricing versions track each pricing data update
CREATE TABLE pricing_versions (
    id SERIAL PRIMARY KEY,
    version VARCHAR(50) UNIQUE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    source VARCHAR(100) NOT NULL,
    metadata JSONB,
    CONSTRAINT only_one_active CHECK (
        is_active = FALSE OR 
        (SELECT COUNT(*) FROM pricing_versions WHERE is_active = TRUE) <= 1
    )
);

CREATE INDEX idx_pricing_versions_active ON pricing_versions(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_pricing_versions_created ON pricing_versions(created_at DESC);

-- AWS services catalog
CREATE TABLE pricing_services (
    id SERIAL PRIMARY KEY,
    service_code VARCHAR(100) NOT NULL,
    service_name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(service_code)
);

CREATE INDEX idx_pricing_services_code ON pricing_services(service_code);

-- AWS regions catalog
CREATE TABLE pricing_regions (
    id SERIAL PRIMARY KEY,
    region_code VARCHAR(50) NOT NULL,
    region_name VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(region_code)
);

CREATE INDEX idx_pricing_regions_code ON pricing_regions(region_code);

-- Pricing dimensions (SKUs with all attributes)
CREATE TABLE pricing_dimensions (
    id SERIAL PRIMARY KEY,
    version_id INTEGER NOT NULL REFERENCES pricing_versions(id) ON DELETE CASCADE,
    service_id INTEGER NOT NULL REFERENCES pricing_services(id),
    region_id INTEGER REFERENCES pricing_regions(id),
    sku VARCHAR(255) NOT NULL,
    product_family VARCHAR(100),
    attributes JSONB NOT NULL,
    unit VARCHAR(50) NOT NULL,
    price_per_unit NUMERIC(20, 10) NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    effective_date TIMESTAMP,
    term_type VARCHAR(50),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(version_id, sku)
);

CREATE INDEX idx_pricing_dimensions_version ON pricing_dimensions(version_id);
CREATE INDEX idx_pricing_dimensions_service ON pricing_dimensions(service_id);
CREATE INDEX idx_pricing_dimensions_region ON pricing_dimensions(region_id);
CREATE INDEX idx_pricing_dimensions_sku ON pricing_dimensions(sku);
CREATE INDEX idx_pricing_dimensions_attributes ON pricing_dimensions USING GIN(attributes);
CREATE INDEX idx_pricing_dimensions_product_family ON pricing_dimensions(product_family);

-- Pricing rules for complex pricing logic (tiered, volume discounts)
CREATE TABLE pricing_rules (
    id SERIAL PRIMARY KEY,
    version_id INTEGER NOT NULL REFERENCES pricing_versions(id) ON DELETE CASCADE,
    service_id INTEGER NOT NULL REFERENCES pricing_services(id),
    rule_type VARCHAR(50) NOT NULL,
    rule_name VARCHAR(255) NOT NULL,
    conditions JSONB NOT NULL,
    formula JSONB NOT NULL,
    priority INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pricing_rules_version ON pricing_rules(version_id);
CREATE INDEX idx_pricing_rules_service ON pricing_rules(service_id);
CREATE INDEX idx_pricing_rules_type ON pricing_rules(rule_type);

-- Free tier definitions
CREATE TABLE pricing_free_tiers (
    id SERIAL PRIMARY KEY,
    version_id INTEGER NOT NULL REFERENCES pricing_versions(id) ON DELETE CASCADE,
    service_id INTEGER NOT NULL REFERENCES pricing_services(id),
    region_id INTEGER REFERENCES pricing_regions(id),
    description TEXT NOT NULL,
    unit VARCHAR(50) NOT NULL,
    quantity NUMERIC(20, 10) NOT NULL,
    period VARCHAR(50) NOT NULL,
    conditions JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pricing_free_tiers_version ON pricing_free_tiers(version_id);
CREATE INDEX idx_pricing_free_tiers_service ON pricing_free_tiers(service_id);

-- ============================================================================
-- JOB TABLES
-- ============================================================================

-- Upload jobs track user submissions
CREATE TABLE upload_jobs (
    id SERIAL PRIMARY KEY,
    job_id UUID UNIQUE NOT NULL,
    upload_type VARCHAR(20) NOT NULL CHECK (upload_type IN ('file', 'folder', 'zip')),
    file_path TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (
        status IN ('pending', 'parsing', 'calculating', 'completed', 'failed')
    ),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    error_message TEXT,
    metadata JSONB
);

CREATE INDEX idx_upload_jobs_job_id ON upload_jobs(job_id);
CREATE INDEX idx_upload_jobs_status ON upload_jobs(status);
CREATE INDEX idx_upload_jobs_created ON upload_jobs(created_at DESC);

-- Analysis results store parsed Terraform and calculated costs
CREATE TABLE analysis_results (
    id SERIAL PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES upload_jobs(job_id) ON DELETE CASCADE,
    pricing_version_id INTEGER NOT NULL REFERENCES pricing_versions(id),
    total_monthly_cost NUMERIC(20, 2) NOT NULL,
    total_resources INTEGER NOT NULL,
    total_supported_resources INTEGER NOT NULL,
    total_unsupported_resources INTEGER NOT NULL,
    breakdown_by_service JSONB NOT NULL,
    breakdown_by_region JSONB NOT NULL,
    warnings JSONB,
    errors JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(job_id)
);

CREATE INDEX idx_analysis_results_job_id ON analysis_results(job_id);
CREATE INDEX idx_analysis_results_pricing_version ON analysis_results(pricing_version_id);

-- Individual resource costs
CREATE TABLE resource_costs (
    id SERIAL PRIMARY KEY,
    analysis_id INTEGER NOT NULL REFERENCES analysis_results(id) ON DELETE CASCADE,
    resource_type VARCHAR(255) NOT NULL,
    resource_name VARCHAR(255) NOT NULL,
    service_code VARCHAR(100) NOT NULL,
    region_code VARCHAR(50),
    monthly_cost NUMERIC(20, 2) NOT NULL,
    attributes JSONB NOT NULL,
    pricing_details JSONB NOT NULL,
    warnings JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_resource_costs_analysis ON resource_costs(analysis_id);
CREATE INDEX idx_resource_costs_service ON resource_costs(service_code);
CREATE INDEX idx_resource_costs_region ON resource_costs(region_code);
CREATE INDEX idx_resource_costs_type ON resource_costs(resource_type);

-- ============================================================================
-- AUDIT TABLES
-- ============================================================================

-- Pricing ingestion logs
CREATE TABLE pricing_ingestion_logs (
    id SERIAL PRIMARY KEY,
    version_id INTEGER REFERENCES pricing_versions(id) ON DELETE SET NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('started', 'completed', 'failed')),
    service_code VARCHAR(100),
    records_processed INTEGER,
    error_message TEXT,
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    metadata JSONB
);

CREATE INDEX idx_pricing_ingestion_logs_version ON pricing_ingestion_logs(version_id);
CREATE INDEX idx_pricing_ingestion_logs_status ON pricing_ingestion_logs(status);
CREATE INDEX idx_pricing_ingestion_logs_started ON pricing_ingestion_logs(started_at DESC);

-- ============================================================================
-- FUNCTIONS AND TRIGGERS
-- ============================================================================

-- Update updated_at timestamp automatically
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_upload_jobs_updated_at
    BEFORE UPDATE ON upload_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- INITIAL DATA
-- ============================================================================

-- Insert common AWS regions
INSERT INTO pricing_regions (region_code, region_name, location) VALUES
    ('us-east-1', 'US East (N. Virginia)', 'US East (N. Virginia)'),
    ('us-east-2', 'US East (Ohio)', 'US East (Ohio)'),
    ('us-west-1', 'US West (N. California)', 'US West (N. California)'),
    ('us-west-2', 'US West (Oregon)', 'US West (Oregon)'),
    ('eu-west-1', 'Europe (Ireland)', 'EU (Ireland)'),
    ('eu-west-2', 'Europe (London)', 'EU (London)'),
    ('eu-west-3', 'Europe (Paris)', 'EU (Paris)'),
    ('eu-central-1', 'Europe (Frankfurt)', 'EU (Frankfurt)'),
    ('ap-south-1', 'Asia Pacific (Mumbai)', 'Asia Pacific (Mumbai)'),
    ('ap-southeast-1', 'Asia Pacific (Singapore)', 'Asia Pacific (Singapore)'),
    ('ap-southeast-2', 'Asia Pacific (Sydney)', 'Asia Pacific (Sydney)'),
    ('ap-northeast-1', 'Asia Pacific (Tokyo)', 'Asia Pacific (Tokyo)'),
    ('ap-northeast-2', 'Asia Pacific (Seoul)', 'Asia Pacific (Seoul)'),
    ('ca-central-1', 'Canada (Central)', 'Canada (Central)'),
    ('sa-east-1', 'South America (São Paulo)', 'South America (Sao Paulo)')
ON CONFLICT (region_code) DO NOTHING;

-- Insert AWS services
INSERT INTO pricing_services (service_code, service_name, description) VALUES
    ('AmazonEC2', 'Amazon Elastic Compute Cloud', 'Virtual servers in the cloud'),
    ('AmazonRDS', 'Amazon Relational Database Service', 'Managed relational database service'),
    ('AmazonS3', 'Amazon Simple Storage Service', 'Object storage service'),
    ('AmazonEBS', 'Amazon Elastic Block Store', 'Block storage for EC2'),
    ('AWSLambda', 'AWS Lambda', 'Serverless compute service')
ON CONFLICT (service_code) DO NOTHING;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE pricing_versions IS 'Tracks pricing data versions and updates';
COMMENT ON TABLE pricing_services IS 'AWS services catalog';
COMMENT ON TABLE pricing_regions IS 'AWS regions catalog';
COMMENT ON TABLE pricing_dimensions IS 'Detailed pricing SKUs with attributes';
COMMENT ON TABLE pricing_rules IS 'Complex pricing rules (tiered, volume discounts)';
COMMENT ON TABLE pricing_free_tiers IS 'AWS Free Tier definitions';
COMMENT ON TABLE upload_jobs IS 'User Terraform file uploads';
COMMENT ON TABLE analysis_results IS 'Cost analysis results';
COMMENT ON TABLE resource_costs IS 'Individual resource cost breakdowns';
COMMENT ON TABLE pricing_ingestion_logs IS 'Pricing data ingestion audit log';
