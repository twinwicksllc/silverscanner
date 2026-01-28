-- Migration: Add time_listed column to deals table
-- Created: 2025-01-28
-- Purpose: Track when listings were created on eBay for longevity analysis

-- Add the time_listed column (nullable for existing records)
ALTER TABLE deals ADD COLUMN IF NOT EXISTS time_listed TIMESTAMP;

-- Create index on time_listed for faster queries
CREATE INDEX IF NOT EXISTS idx_deals_time_listed ON deals(time_listed);

-- Log the migration
INSERT INTO migration_history (migration_name, applied_at, status)
VALUES ('add_time_listed_column', NOW(), 'completed')
ON CONFLICT (migration_name) DO NOTHING;