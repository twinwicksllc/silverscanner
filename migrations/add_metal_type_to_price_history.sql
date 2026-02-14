-- Migration: Add metal_type column to price_history table
-- This enables tracking price history for multiple metals (gold, silver, etc.)

-- Add metal_type column with default value 'silver'
ALTER TABLE price_history ADD COLUMN IF NOT EXISTS metal_type VARCHAR(20) DEFAULT 'silver';

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_price_history_metal_type ON price_history(metal_type);

-- Update existing records to have metal_type = 'silver'
UPDATE price_history SET metal_type = 'silver' WHERE metal_type IS NULL OR metal_type = '';

-- Add composite index for (metal_type, timestamp) for faster filtered queries
CREATE INDEX IF NOT EXISTS idx_price_history_metal_timestamp ON price_history(metal_type, timestamp);