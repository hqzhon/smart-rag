-- Add missing vectorization_time column to documents table
-- This fixes the error: Unknown column 'vectorization_time' in 'field list'

USE medical_rag;

-- Add the vectorization_time column if it doesn't exist
ALTER TABLE documents 
ADD COLUMN IF NOT EXISTS vectorization_time TIMESTAMP NULL COMMENT 'Vectorization completion time';

-- Verify the column was added
SHOW COLUMNS FROM documents LIKE 'vectorization_time';

-- Optional: Update existing records to set vectorization_time for completed documents
UPDATE documents 
SET vectorization_time = updated_at 
WHERE vectorization_status = 'completed' AND vectorization_time IS NULL;

SELECT 'vectorization_time column added successfully' AS status;