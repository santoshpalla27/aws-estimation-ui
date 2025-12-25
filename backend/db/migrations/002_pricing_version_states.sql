-- Add pricing version status enum and constraints
-- This migration ensures exactly one ACTIVE pricing version at any time

-- Create status enum type
CREATE TYPE pricing_version_status AS ENUM ('DRAFT', 'VALIDATED', 'ACTIVE', 'ARCHIVED');

-- Add status column to pricing_versions
ALTER TABLE pricing_versions 
ADD COLUMN status pricing_version_status NOT NULL DEFAULT 'DRAFT';

-- Add validation columns
ALTER TABLE pricing_versions
ADD COLUMN validated_at TIMESTAMP,
ADD COLUMN validated_by VARCHAR(255),
ADD COLUMN validation_errors JSONB,
ADD COLUMN activated_at TIMESTAMP,
ADD COLUMN activated_by VARCHAR(255),
ADD COLUMN archived_at TIMESTAMP,
ADD COLUMN archived_by VARCHAR(255);

-- Create unique partial index to enforce single ACTIVE version
-- This is the DATABASE CONSTRAINT that prevents multiple active versions
CREATE UNIQUE INDEX idx_pricing_versions_single_active 
ON pricing_versions (status) 
WHERE status = 'ACTIVE';

-- Create index for fast active version lookup
CREATE INDEX idx_pricing_versions_active 
ON pricing_versions (status, created_at DESC) 
WHERE status = 'ACTIVE';

-- Create index for version lifecycle queries
CREATE INDEX idx_pricing_versions_status_created 
ON pricing_versions (status, created_at DESC);

-- Add check constraint for state transition timestamps
ALTER TABLE pricing_versions
ADD CONSTRAINT chk_validated_timestamp 
CHECK (
    (status IN ('VALIDATED', 'ACTIVE', 'ARCHIVED') AND validated_at IS NOT NULL) OR
    (status = 'DRAFT' AND validated_at IS NULL)
);

ALTER TABLE pricing_versions
ADD CONSTRAINT chk_activated_timestamp 
CHECK (
    (status IN ('ACTIVE', 'ARCHIVED') AND activated_at IS NOT NULL) OR
    (status IN ('DRAFT', 'VALIDATED') AND activated_at IS NULL)
);

ALTER TABLE pricing_versions
ADD CONSTRAINT chk_archived_timestamp 
CHECK (
    (status = 'ARCHIVED' AND archived_at IS NOT NULL) OR
    (status IN ('DRAFT', 'VALIDATED', 'ACTIVE') AND archived_at IS NULL)
);

-- Update existing is_active column to match status
-- Keep is_active for backward compatibility but derive from status
UPDATE pricing_versions 
SET status = CASE 
    WHEN is_active = true THEN 'ACTIVE'::pricing_version_status
    ELSE 'DRAFT'::pricing_version_status
END;

-- Add trigger to keep is_active in sync with status
CREATE OR REPLACE FUNCTION sync_pricing_version_active()
RETURNS TRIGGER AS $$
BEGIN
    NEW.is_active := (NEW.status = 'ACTIVE');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_sync_pricing_version_active
BEFORE INSERT OR UPDATE ON pricing_versions
FOR EACH ROW
EXECUTE FUNCTION sync_pricing_version_active();

-- Add comment explaining the constraint
COMMENT ON INDEX idx_pricing_versions_single_active IS 
'Ensures exactly one ACTIVE pricing version exists at any time. This is a critical business rule.';

COMMENT ON COLUMN pricing_versions.status IS 
'Version lifecycle: DRAFT → VALIDATED → ACTIVE → ARCHIVED. Only one ACTIVE version allowed.';
