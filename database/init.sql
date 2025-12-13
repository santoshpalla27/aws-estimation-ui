-- AWS Cost Estimation Platform - Database Schema
-- PostgreSQL 15+

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    meta_data JSONB DEFAULT '{}'::jsonb
);

-- Infrastructure graphs
CREATE TABLE IF NOT EXISTS infrastructure_graphs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    nodes JSONB NOT NULL DEFAULT '[]'::jsonb,
    edges JSONB NOT NULL DEFAULT '[]'::jsonb,
    meta_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Cost estimates
CREATE TABLE IF NOT EXISTS cost_estimates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    graph_id UUID REFERENCES infrastructure_graphs(id) ON DELETE SET NULL,
    total_monthly_cost DECIMAL(12, 2) NOT NULL,
    breakdown JSONB NOT NULL,
    warnings JSONB DEFAULT '[]'::jsonb,
    assumptions JSONB DEFAULT '[]'::jsonb,
    confidence DECIMAL(3, 2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Pricing data cache
CREATE TABLE IF NOT EXISTS pricing_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service VARCHAR(100) NOT NULL,
    region VARCHAR(50) NOT NULL,
    sku VARCHAR(255) NOT NULL,
    attributes JSONB NOT NULL,
    pricing JSONB NOT NULL,
    effective_date DATE NOT NULL,
    version VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Pricing versions tracking
CREATE TABLE IF NOT EXISTS pricing_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service VARCHAR(100) NOT NULL,
    region VARCHAR(50) NOT NULL,
    version VARCHAR(50) NOT NULL,
    sku_count INTEGER NOT NULL,
    synced_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(service, region, version)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_graphs_project_id ON infrastructure_graphs(project_id);
CREATE INDEX IF NOT EXISTS idx_estimates_project_id ON cost_estimates(project_id);
CREATE INDEX IF NOT EXISTS idx_estimates_created_at ON cost_estimates(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pricing_service_region ON pricing_data(service, region);
CREATE INDEX IF NOT EXISTS idx_pricing_sku ON pricing_data(sku);
CREATE INDEX IF NOT EXISTS idx_pricing_attributes_gin ON pricing_data USING GIN(attributes);
CREATE INDEX IF NOT EXISTS idx_pricing_effective_date ON pricing_data(effective_date DESC);

-- Updated timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_graphs_updated_at BEFORE UPDATE ON infrastructure_graphs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_pricing_updated_at BEFORE UPDATE ON pricing_data
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert sample project for testing
INSERT INTO projects (name, description, meta_data) VALUES
    ('Sample 3-Tier Web App', 'Example architecture with VPC, ALB, EC2, and RDS', '{"tags": ["example", "web-app"]}'::jsonb)
ON CONFLICT DO NOTHING;
