-- ============================================================================
-- ZeroTrace All-In-One Supabase Database Schema & Storage Configuration
-- File: supabase_config/schema.sql
--
-- This single unified script performs:
-- 1. Extension initialization
-- 2. Safe core table creation & migration (certificates, user_profiles)
-- 3. Historical certificate preservation on user deletion (ON DELETE SET NULL)
-- 4. Cleanup of legacy tables (wipe_logs, verification_logs, pin_hash, json_url)
-- 5. Automatic profile provisioning and updated_at triggers
-- 6. Row Level Security (RLS) policies with strict backend authority
-- 7. Private Supabase Storage bucket configuration for certificates (PDF only)
--
-- Safe to execute on both a brand-new Supabase project and an existing database.
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- 1. CORE TABLE: certificates
-- ============================================================================

CREATE TABLE IF NOT EXISTS certificates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cert_id TEXT UNIQUE NOT NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    idempotency_key TEXT UNIQUE,
    device_id TEXT NOT NULL,
    device_name TEXT,
    device_model TEXT,
    device_serial TEXT,
    wipe_method TEXT NOT NULL,
    sanitization_level TEXT NOT NULL DEFAULT 'Clear' CHECK (sanitization_level IN ('Purge', 'Clear', 'Inconclusive/Failed')),
    validation_status TEXT NOT NULL DEFAULT 'Verified' CHECK (validation_status IN ('Verified', 'Pending', 'Revoked', 'Inconclusive', 'Failed')),
    validation_summary JSONB,
    policy_version TEXT DEFAULT '1.0.0',
    signing_key_id TEXT DEFAULT 'zerotrace-authoritative-p256-v1',
    verification_hash TEXT NOT NULL,
    signature TEXT NOT NULL,
    pdf_url TEXT,
    status TEXT DEFAULT 'Verified' CHECK (status IN ('Verified', 'Pending', 'Revoked')),
    revoked_at TIMESTAMPTZ,
    revoked_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    revocation_reason TEXT,
    revocation_ip TEXT,
    revocation_user_agent TEXT,
    wipe_start_time TIMESTAMPTZ,
    wipe_end_time TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Safe column additions if migrating an existing certificates table
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'certificates') THEN
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'certificates' AND column_name = 'sanitization_level') THEN
            ALTER TABLE certificates ADD COLUMN sanitization_level TEXT NOT NULL DEFAULT 'Clear';
        END IF;

        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'certificates' AND column_name = 'validation_status') THEN
            ALTER TABLE certificates ADD COLUMN validation_status TEXT NOT NULL DEFAULT 'Verified';
        END IF;

        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'certificates' AND column_name = 'validation_summary') THEN
            ALTER TABLE certificates ADD COLUMN validation_summary JSONB;
        END IF;

        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'certificates' AND column_name = 'policy_version') THEN
            ALTER TABLE certificates ADD COLUMN policy_version TEXT DEFAULT '1.0.0';
        END IF;

        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'certificates' AND column_name = 'signing_key_id') THEN
            ALTER TABLE certificates ADD COLUMN signing_key_id TEXT DEFAULT 'zerotrace-authoritative-p256-v1';
        END IF;

        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'certificates' AND column_name = 'idempotency_key') THEN
            ALTER TABLE certificates ADD COLUMN idempotency_key TEXT;
        END IF;

        -- Drop json_url if exists (JSON generation is removed)
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'certificates' AND column_name = 'json_url') THEN
            ALTER TABLE certificates DROP COLUMN json_url;
        END IF;

        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'certificates' AND column_name = 'revoked_at') THEN
            ALTER TABLE certificates ADD COLUMN revoked_at TIMESTAMPTZ;
        END IF;

        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'certificates' AND column_name = 'revoked_by') THEN
            ALTER TABLE certificates ADD COLUMN revoked_by UUID REFERENCES auth.users(id) ON DELETE SET NULL;
        END IF;

        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'certificates' AND column_name = 'revocation_reason') THEN
            ALTER TABLE certificates ADD COLUMN revocation_reason TEXT;
        END IF;

        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'certificates' AND column_name = 'revocation_ip') THEN
            ALTER TABLE certificates ADD COLUMN revocation_ip TEXT;
        END IF;

        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'certificates' AND column_name = 'revocation_user_agent') THEN
            ALTER TABLE certificates ADD COLUMN revocation_user_agent TEXT;
        END IF;
    END IF;
END $$;

-- Ensure ON DELETE SET NULL foreign key constraint exists for certificates.user_id
DO $$
DECLARE
    fk_name TEXT;
BEGIN
    SELECT tc.constraint_name INTO fk_name
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_name = kcu.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY'
      AND tc.table_name = 'certificates'
      AND kcu.column_name = 'user_id'
    LIMIT 1;

    IF fk_name IS NOT NULL THEN
        EXECUTE 'ALTER TABLE certificates DROP CONSTRAINT ' || quote_ident(fk_name);
    END IF;

    ALTER TABLE certificates
        ADD CONSTRAINT certificates_user_id_fkey
        FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE SET NULL;
EXCEPTION
    WHEN OTHERS THEN
        NULL;
END $$;

-- Certificates Indices
CREATE INDEX IF NOT EXISTS idx_certificates_cert_id ON certificates(cert_id);
CREATE INDEX IF NOT EXISTS idx_certificates_user_id ON certificates(user_id);
CREATE INDEX IF NOT EXISTS idx_certificates_verification_hash ON certificates(verification_hash);
CREATE UNIQUE INDEX IF NOT EXISTS idx_certificates_idempotency_key ON certificates(idempotency_key);
CREATE INDEX IF NOT EXISTS idx_certificates_validation_status ON certificates(validation_status);


-- ============================================================================
-- 2. CORE TABLE: user_profiles
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT,
    organization TEXT,
    phone TEXT,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'deactivated', 'deleted')),
    deactivated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Safe modifications for existing user_profiles
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'user_profiles') THEN
        -- Remove server-side pin_hash (authentication uses Supabase auth, local app uses bcrypt)
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'user_profiles' AND column_name = 'pin_hash') THEN
            ALTER TABLE user_profiles DROP COLUMN pin_hash;
        END IF;

        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'user_profiles' AND column_name = 'status') THEN
            ALTER TABLE user_profiles ADD COLUMN status TEXT DEFAULT 'active' CHECK (status IN ('active', 'deactivated', 'deleted'));
        END IF;

        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'user_profiles' AND column_name = 'deactivated_at') THEN
            ALTER TABLE user_profiles ADD COLUMN deactivated_at TIMESTAMPTZ;
        END IF;
    END IF;
END $$;


-- ============================================================================
-- 3. CLEANUP NON-CORE TABLES
-- Only `certificates` and `user_profiles` are maintained.
-- ============================================================================

DROP TABLE IF EXISTS wipe_logs CASCADE;
DROP TABLE IF EXISTS verification_logs CASCADE;
DROP TABLE IF EXISTS wipe_submissions CASCADE;
DROP TABLE IF EXISTS certificate_revocation_logs CASCADE;


-- ============================================================================
-- 4. TRIGGERS & AUTOMATION
-- ============================================================================

-- Automatically create user_profile when a user registers
CREATE OR REPLACE FUNCTION handle_new_user_profile()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    INSERT INTO public.user_profiles (id, full_name)
    VALUES (NEW.id, COALESCE(NEW.raw_user_meta_data->>'full_name', ''))
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION handle_new_user_profile();

-- Auto-update updated_at timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_certificates_updated_at ON certificates;
CREATE TRIGGER update_certificates_updated_at
    BEFORE UPDATE ON certificates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_profiles_updated_at ON user_profiles;
CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ============================================================================
-- 5. ROW LEVEL SECURITY (RLS) POLICIES
-- Strict backend authority: Client apps have NO direct write access to certificates.
-- Only backend service_role can issue, update, or revoke certificates.
-- ============================================================================

ALTER TABLE certificates ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

-- Certificates Policies
DROP POLICY IF EXISTS "Service role full access on certificates" ON certificates;
CREATE POLICY "Service role full access on certificates"
ON certificates FOR ALL
USING ((select auth.jwt())->>'role' = 'service_role')
WITH CHECK ((select auth.jwt())->>'role' = 'service_role');

DROP POLICY IF EXISTS "Public can view certificates for verification" ON certificates;
CREATE POLICY "Public can view certificates for verification"
ON certificates FOR SELECT
USING (true);

DROP POLICY IF EXISTS "Authenticated users can view own certificates" ON certificates;
CREATE POLICY "Authenticated users can view own certificates"
ON certificates FOR SELECT
TO authenticated
USING (auth.uid() = user_id OR user_id IS NULL);

-- User Profiles Policies
DROP POLICY IF EXISTS "Service role full access on user_profiles" ON user_profiles;
CREATE POLICY "Service role full access on user_profiles"
ON user_profiles FOR ALL
USING ((select auth.jwt())->>'role' = 'service_role')
WITH CHECK ((select auth.jwt())->>'role' = 'service_role');

DROP POLICY IF EXISTS "Users can view own profile" ON user_profiles;
CREATE POLICY "Users can view own profile"
ON user_profiles FOR SELECT
TO authenticated
USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can update own profile" ON user_profiles;
CREATE POLICY "Users can update own profile"
ON user_profiles FOR UPDATE
TO authenticated
USING (auth.uid() = id)
WITH CHECK (auth.uid() = id);

DROP POLICY IF EXISTS "Users can delete own profile" ON user_profiles;
CREATE POLICY "Users can delete own profile"
ON user_profiles FOR DELETE
TO authenticated
USING (auth.uid() = id);


-- ============================================================================
-- 6. PRIVATE STORAGE BUCKET (`certificates`) & STORAGE POLICIES
-- Signed PDFs are stored in a private Supabase Storage bucket.
-- Allowed MIME types: application/pdf only.
-- ============================================================================

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'certificates',
    'certificates',
    false, -- Private bucket
    10485760, -- 10MB limit
    ARRAY['application/pdf']
)
ON CONFLICT (id) DO UPDATE SET
    public = false,
    allowed_mime_types = ARRAY['application/pdf'];

DROP POLICY IF EXISTS "Service role full access on certificates bucket" ON storage.objects;
CREATE POLICY "Service role full access on certificates bucket"
ON storage.objects FOR ALL
USING (
    bucket_id = 'certificates' AND
    (select auth.jwt())->>'role' = 'service_role'
)
WITH CHECK (
    bucket_id = 'certificates' AND
    (select auth.jwt())->>'role' = 'service_role'
);

DROP POLICY IF EXISTS "Authenticated users can read own certificates in storage" ON storage.objects;
CREATE POLICY "Authenticated users can read own certificates in storage"
ON storage.objects FOR SELECT
TO authenticated
USING (
    bucket_id = 'certificates' AND
    (storage.foldername(name))[1] = (select auth.uid()::text)
);
