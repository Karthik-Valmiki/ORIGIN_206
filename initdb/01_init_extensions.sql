-- Common extensions useful for LMPC Verification System
-- UUID generation for inspections, images, evidence, findings, rules
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Trigram matching for fuzzy search on extracted text, manufacturer names, etc.
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- B-Tree GIN for fast indexing on combined JSONB / scalar columns
CREATE EXTENSION IF NOT EXISTS "btree_gin";
