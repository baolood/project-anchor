-- Ensure commands_domain.result column is JSONB (not plain text)
-- This migration is idempotent and safe to run multiple times.

DO $$
BEGIN
    -- Only alter when the column exists and is NOT already jsonb
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'commands_domain'
          AND column_name = 'result'
          AND data_type <> 'jsonb'
    ) THEN
        ALTER TABLE commands_domain
        ALTER COLUMN result
        TYPE jsonb
        USING
          CASE
              WHEN result IS NULL OR trim(result::text) = '' THEN NULL
              ELSE result::jsonb
          END;
    END IF;
END $$;

