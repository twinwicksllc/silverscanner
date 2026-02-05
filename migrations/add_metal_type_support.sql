-- Migration: Add Multi-Metal Support
-- Date: 2026-02-04
-- Description: Add columns to support gold, platinum, and palladium

-- Add metal_type column (default to 'silver' for existing records)
ALTER TABLE deals ADD COLUMN IF NOT EXISTS metal_type VARCHAR(20) DEFAULT 'silver';

-- Add metal_purity column (1.0 = pure, 0.9 = 90%, etc.)
ALTER TABLE deals ADD COLUMN IF NOT EXISTS metal_purity FLOAT DEFAULT 1.0;

-- Rename silver_weight_oz to metal_weight_oz for consistency
-- First check if the column exists
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'deals' AND column_name = 'silver_weight_oz'
    ) THEN
        ALTER TABLE deals RENAME COLUMN silver_weight_oz TO metal_weight_oz;
    END IF;
END $$;

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_deals_metal_type ON deals(metal_type);
CREATE INDEX IF NOT EXISTS idx_deals_metal_weight ON deals(metal_weight_oz);

-- Create spot_prices table for tracking multiple metals
CREATE TABLE IF NOT EXISTS spot_prices (
    id SERIAL PRIMARY KEY,
    metal_type VARCHAR(20) NOT NULL,
    price FLOAT NOT NULL,
    source VARCHAR(100),
    timestamp TIMESTAMP DEFAULT NOW(),
    verified BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_spot_prices_metal_timestamp ON spot_prices(metal_type, timestamp DESC);

-- Update existing price_history to support multiple metals
ALTER TABLE price_history ADD COLUMN IF NOT EXISTS metal_type VARCHAR(20) DEFAULT 'silver';
CREATE INDEX IF NOT EXISTS idx_price_history_metal ON price_history(metal_type, timestamp DESC);
