-- Add result column to commands table if it doesn't exist
-- This migration is idempotent and can be run multiple times safely

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'commands'
        AND column_name = 'result'
    ) THEN
        ALTER TABLE commands ADD COLUMN result JSONB;
    END IF;
END $$;
