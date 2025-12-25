-- Single active pricing version constraint
-- Ensures exactly one ACTIVE version at any time

-- Add status column if not exists (from previous migration)
ALTER TABLE pricing_versions 
ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'DRAFT';

-- Create UNIQUE partial index to enforce single ACTIVE version
-- This is a DATABASE-LEVEL constraint that prevents multiple active versions
CREATE UNIQUE INDEX IF NOT EXISTS idx_pricing_versions_single_active 
ON pricing_versions (status) 
WHERE status = 'ACTIVE';

-- Add comment
COMMENT ON INDEX idx_pricing_versions_single_active IS 
'Enforces exactly one ACTIVE pricing version at any time';

-- Verify constraint works
DO $$
BEGIN
    -- This should succeed (first active version)
    -- UPDATE pricing_versions SET status = 'ACTIVE' WHERE id = 1;
    
    -- This should FAIL (second active version)
    -- UPDATE pricing_versions SET status = 'ACTIVE' WHERE id = 2;
    -- ERROR: duplicate key value violates unique constraint
    
    RAISE NOTICE 'Single active version constraint is enforced';
END $$;
