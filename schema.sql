-- ============================================================================
-- SIH26034 LMPC VERIFICATION SYSTEM
-- PostgreSQL - SINGLE DATABASE INITIALIZATION FILE
-- ============================================================================
-- This file contains the complete PostgreSQL schema for the application.
-- Run this file as one unit during database initialization.
-- Application logic (OCR, rule evaluation, job processing, etc.) remains
-- outside PostgreSQL.
-- ============================================================================

-- ==========================================
-- ENABLE REQUIRED EXTENSIONS
-- ==========================================
CREATE EXTENSION IF NOT EXISTS "citext";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- ==========================================
-- AUTOMATED updated_at TRIGGER FUNCTION
-- ==========================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ==========================================
-- SEQUENCES
-- ==========================================
CREATE SEQUENCE IF NOT EXISTS inspection_number_seq START WITH 1;

-- ==========================================
-- INSPECTION NUMBER AUTO-GENERATOR TRIGGER
-- (FIX #1: NEXTVAL cannot be used in DEFAULT)
-- ==========================================
CREATE OR REPLACE FUNCTION generate_inspection_number()
RETURNS TRIGGER AS $$
BEGIN
    NEW.inspection_number :=
        'INSP-' ||
        TO_CHAR(CURRENT_DATE, 'YYYYMMDD') || '-' ||
        LPAD(NEXTVAL('inspection_number_seq')::TEXT, 6, '0');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ==========================================
-- 1. ACCESS CONTROL & USERS (RBAC)
-- ==========================================

CREATE TABLE roles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_name       VARCHAR(50)  UNIQUE NOT NULL,   -- 'ADMIN', 'OFFICER'
    description     TEXT,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE permissions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    permission_name VARCHAR(100) UNIQUE NOT NULL,
    resource        VARCHAR(50)  NOT NULL,
    action          VARCHAR(50)  NOT NULL,           -- 'CREATE','READ','UPDATE','DELETE','APPROVE'
    description     TEXT
);

CREATE TABLE role_permissions (
    role_id         UUID REFERENCES roles(id)       ON DELETE CASCADE,
    permission_id   UUID REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name       VARCHAR(100) NOT NULL,
    email           CITEXT UNIQUE NOT NULL,          -- case-insensitive
    password_hash   VARCHAR(255) NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE user_roles (
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    role_id         UUID REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at     TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, role_id)
);


-- ==========================================
-- 2. PRODUCT CATEGORIES
-- ==========================================

CREATE TABLE product_categories (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_name   VARCHAR(100) UNIQUE NOT NULL,
    description     TEXT
);


-- ==========================================
-- 3. RULES & APPLICABILITY ENGINE
-- ==========================================

CREATE TABLE rule_sets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) UNIQUE NOT NULL,
    description     TEXT
);

CREATE TABLE rule_versions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_set_id     UUID NOT NULL REFERENCES rule_sets(id) ON DELETE CASCADE,
    version_number  VARCHAR(50) NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    effective_from  TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_rule_set_version UNIQUE (rule_set_id, version_number)
);

CREATE TABLE rules (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_version_id UUID NOT NULL REFERENCES rule_versions(id) ON DELETE CASCADE,
    rule_code       VARCHAR(50) NOT NULL,
    check_type      VARCHAR(50) NOT NULL,
    description     TEXT,
    parameters      JSONB,
    CONSTRAINT chk_check_type CHECK (check_type IN (
        'PRESENCE', 'VALUE', 'FORMAT', 'UNIT',
        'PLACEMENT', 'LEGIBILITY', 'VISUAL', 'DECLARATION'
    )),
    CONSTRAINT uq_version_rule_code UNIQUE (rule_version_id, rule_code)
);

CREATE TABLE rule_applicability (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_category_id     UUID NOT NULL REFERENCES product_categories(id) ON DELETE CASCADE,
    rule_version_id         UUID NOT NULL REFERENCES rule_versions(id)      ON DELETE CASCADE,
    commodity_package_type  VARCHAR(100) NOT NULL,
    is_imported             BOOLEAN NOT NULL DEFAULT FALSE,
    retail_context          VARCHAR(50),
    applicable_exceptions   JSONB,
    special_provisions      JSONB,
    -- FIX #4: date-range for Rule Version Lock
    effective_from          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    effective_until         TIMESTAMP WITH TIME ZONE,
    CONSTRAINT uq_category_version_context UNIQUE (
        product_category_id, rule_version_id,
        commodity_package_type, is_imported, retail_context
    )
);


-- ==========================================
-- 4. INSPECTION PIPELINE
-- ==========================================

CREATE TABLE inspections (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- FIX #1: NULL here; trigger fills it on INSERT
    inspection_number       VARCHAR(50) UNIQUE,
    officer_id              UUID REFERENCES users(id)              ON DELETE SET NULL,
    product_category_id     UUID NOT NULL REFERENCES product_categories(id) ON DELETE RESTRICT,
    rule_version_id         UUID NOT NULL REFERENCES rule_versions(id)      ON DELETE RESTRICT,
    status                  VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_inspection_status CHECK (status IN (
        'PENDING', 'PROCESSING', 'COMPLIANT',
        'NON_COMPLIANT', 'REVIEW_REQUIRED', 'PROCESSING_FAILED'
    ))
);

CREATE TRIGGER trg_inspections_number
    BEFORE INSERT ON inspections
    FOR EACH ROW WHEN (NEW.inspection_number IS NULL)
    EXECUTE FUNCTION generate_inspection_number();

CREATE TRIGGER trg_inspections_updated_at
    BEFORE UPDATE ON inspections
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ==========================================
-- 5. IMAGE PIPELINE & QUALITY ASSESSMENT
-- ==========================================

CREATE TABLE images (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inspection_id           UUID NOT NULL REFERENCES inspections(id) ON DELETE CASCADE,
    file_path               VARCHAR(512) NOT NULL,             -- object storage key / local path
    is_valid_file           BOOLEAN NOT NULL DEFAULT TRUE,
    resolution_width        INT   CHECK (resolution_width  > 0),
    resolution_height       INT   CHECK (resolution_height > 0),
    blur_score              FLOAT CHECK (blur_score        BETWEEN 0.0 AND 1.0),
    glare_score             FLOAT CHECK (glare_score       BETWEEN 0.0 AND 1.0),
    reflection_score        FLOAT CHECK (reflection_score  BETWEEN 0.0 AND 1.0),
    orientation_angle       INT   CHECK (orientation_angle IN (0, 90, 180, 270)),
    preprocessing_status    VARCHAR(50) NOT NULL DEFAULT 'UNPROCESSED',
    -- FIX #3: separate OCR status for state-machine tracking
    ocr_status              VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    uploaded_at             TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_preprocessing_status CHECK (preprocessing_status IN (
        'UNPROCESSED', 'PROCESSING', 'COMPLETED', 'FAILED'
    )),
    CONSTRAINT chk_ocr_status CHECK (ocr_status IN (
        'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'SKIPPED'
    ))
);

CREATE TABLE image_processing_history (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    image_id            UUID NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    step_name           VARCHAR(100) NOT NULL,   -- 'RESIZE','DENOISE','SHARPEN','PERSPECTIVE_CORRECTION'
    status              VARCHAR(50)  NOT NULL,
    parameters          JSONB,
    execution_time_ms   INT,
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_history_status CHECK (status IN ('STARTED', 'COMPLETED', 'FAILED'))
);


-- ==========================================
-- 6. OCR RESULTS
-- ==========================================

CREATE TABLE ocr_results (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inspection_id       UUID NOT NULL REFERENCES inspections(id) ON DELETE CASCADE,
    image_id            UUID NOT NULL REFERENCES images(id)      ON DELETE CASCADE,
    detected_text       TEXT NOT NULL,
    bounding_box        JSONB NOT NULL,      -- {x1,y1,x2,y2} or polygon points
    confidence_score    FLOAT CHECK (confidence_score BETWEEN 0.0 AND 1.0),
    language            VARCHAR(20) DEFAULT 'en'
);


-- ==========================================
-- 7. FIELD EXTRACTION & NORMALIZATION
-- ==========================================

CREATE TABLE extracted_fields (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inspection_id       UUID NOT NULL REFERENCES inspections(id) ON DELETE CASCADE,
    ocr_result_id       UUID          REFERENCES ocr_results(id)  ON DELETE SET NULL,
    field_type          VARCHAR(50)  NOT NULL,
    raw_value           TEXT,
    normalized_value    TEXT,
    -- FIX #2: free-text unit; validated at application layer
    unit                VARCHAR(30),
    is_validated        BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT chk_field_type CHECK (field_type IN (
        'MRP', 'QUANTITY', 'MANUFACTURER', 'IMPORTER',
        'COUNTRY_OF_ORIGIN', 'DATES', 'CONSUMER_CARE',
        'PRODUCT_NAME', 'OTHER'
    ))
);


-- ==========================================
-- 8. FINDINGS & EVIDENCE
-- ==========================================

CREATE TABLE findings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inspection_id   UUID NOT NULL REFERENCES inspections(id) ON DELETE CASCADE,
    rule_id         UUID          REFERENCES rules(id)       ON DELETE SET NULL,
    -- FIX #5: constrained finding_type
    finding_type    VARCHAR(50) NOT NULL,
    status          VARCHAR(50) NOT NULL,
    details         JSONB,
    CONSTRAINT chk_finding_type CHECK (finding_type IN (
        'PRESENCE', 'VALUE', 'FORMAT', 'UNIT',
        'PLACEMENT', 'LEGIBILITY', 'VISUAL', 'DECLARATION'
    )),
    CONSTRAINT chk_finding_status CHECK (status IN ('PASS', 'FAIL', 'AMBIGUOUS'))
);

CREATE TABLE evidences (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inspection_id           UUID NOT NULL REFERENCES inspections(id) ON DELETE CASCADE,
    finding_id              UUID NOT NULL REFERENCES findings(id)    ON DELETE CASCADE,
    ocr_result_id           UUID          REFERENCES ocr_results(id) ON DELETE SET NULL,
    image_crop_path         VARCHAR(512),
    highlighted_image_path  VARCHAR(512),
    fusion_confidence       FLOAT CHECK (fusion_confidence BETWEEN 0.0 AND 1.0)
);


-- ==========================================
-- 9. OFFICER REVIEW & REPORTS
-- ==========================================

CREATE TABLE reviews (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inspection_id   UUID NOT NULL REFERENCES inspections(id) ON DELETE CASCADE,
    officer_id      UUID          REFERENCES users(id)       ON DELETE SET NULL,
    action          VARCHAR(50)  NOT NULL,
    comments        TEXT,
    reviewed_at     TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_review_action CHECK (action IN (
        'ACCEPT', 'OVERRIDE', 'REQUEST_REINSPECTION'
    ))
);

CREATE TABLE reports (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inspection_id       UUID UNIQUE NOT NULL REFERENCES inspections(id) ON DELETE CASCADE,
    -- object storage key (S3/MinIO path)
    report_storage_key  VARCHAR(512) NOT NULL,
    generated_at        TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);


-- ==========================================
-- 10. AUDIT LOGS
-- ==========================================

CREATE TABLE audit_logs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id) ON DELETE SET NULL,
    action      VARCHAR(100) NOT NULL,
    entity_name VARCHAR(100) NOT NULL,
    entity_id   UUID,
    payload     JSONB,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);


-- ==========================================
-- INDEXING STRATEGY
-- ==========================================

-- Inspections: officer workload + status dashboards
CREATE INDEX idx_inspections_officer_created   ON inspections(officer_id, created_at DESC);
CREATE INDEX idx_inspections_status_created    ON inspections(status, created_at DESC);

-- Images
CREATE INDEX idx_images_inspection             ON images(inspection_id);
CREATE INDEX idx_images_preprocessing_status   ON images(preprocessing_status);
CREATE INDEX idx_images_ocr_status             ON images(ocr_status);

-- Image processing history
CREATE INDEX idx_img_hist_image                ON image_processing_history(image_id);

-- OCR Results: most common join is (inspection_id, image_id)
CREATE INDEX idx_ocr_insp_image                ON ocr_results(inspection_id, image_id);

-- Extracted fields
CREATE INDEX idx_extracted_inspection          ON extracted_fields(inspection_id);
CREATE INDEX idx_extracted_ocr                 ON extracted_fields(ocr_result_id);
CREATE INDEX idx_extracted_field_type          ON extracted_fields(inspection_id, field_type);

-- Findings & evidences
CREATE INDEX idx_findings_inspection           ON findings(inspection_id);
CREATE INDEX idx_evidences_finding             ON evidences(finding_id);

-- Rule applicability date-range queries
CREATE INDEX idx_rule_app_dates                ON rule_applicability(effective_from, effective_until);

-- Audit
CREATE INDEX idx_audit_user                    ON audit_logs(user_id);
CREATE INDEX idx_audit_entity                  ON audit_logs(entity_name, entity_id);
CREATE INDEX idx_audit_created                 ON audit_logs(created_at DESC);