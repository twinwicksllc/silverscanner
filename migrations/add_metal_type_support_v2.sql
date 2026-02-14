-- Migration: Add Multi-Metal Support
-- Date: 2026-02-05
-- Description: Add columns to support gold, platinum, and palladium
-- Compatible with both PostgreSQL and SQLite

-- Add metal_type column (default to 'silver' for existing records)
ALTER TABLE deals ADD COLUMN metal_type VARCHAR(20) DEFAULT 'silver';

-- Add metal_purity column (1.0 = pure, 0.9 = 90%, etc.)
ALTER TABLE deals ADD COLUMN metal_purity FLOAT DEFAULT 1.0;

-- Add indexes for performance
CREATE INDEX idx_deals_metal_type ON deals(metal_type);

-- Create spot_prices table for tracking multiple metals
CREATE TABLE spot_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metal_type VARCHAR(20) NOT NULL,
    price FLOAT NOT NULL,
    source VARCHAR(100),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    verified BOOLEAN DEFAULT 0
);

CREATE INDEX idx_spot_prices_metal_timestamp ON spot_prices(metal_type, timestamp DESC);

-- Update existing price_history to support multiple metals
ALTER TABLE price_history ADD COLUMN metal_type VARCHAR(20) DEFAULT 'silver';
CREATE INDEX idx_price_history_metal ON price_history(metal_type, timestamp DESC);