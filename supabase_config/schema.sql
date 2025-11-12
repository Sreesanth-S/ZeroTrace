-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Certificates Table
CREATE TABLE certificates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    device_id TEXT NOT NULL,
    cert_id TEXT UNIQUE NOT NULL,
    device_name TEXT,
    device_model TEXT,
    device_serial TEXT,
    wipe_method TEXT NOT NULL,
    verification_hash TEXT NOT NULL,
    pdf_url TEXT,
    json_url TEXT,
    signature TEXT NOT NULL,
    status TEXT DEFAULT 'verified' CHECK (status IN ('verified', 'pending', 'revoked')),
    wipe_start_time TIMESTAMPTZ,
    wipe_end_time TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for faster lookups
CREATE INDEX idx_certificates_cert_id ON certificates(cert_id);
CREATE INDEX idx_certificates_user_id ON certificates(user_id);
CREATE INDEX idx_certificates_verification_hash ON certificates(verification_hash);

-- User Profiles Table (optional extended user info)
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT,
    organization TEXT,
    phone TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Wipe Logs Table (for detailed tracking)
CREATE TABLE wipe_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    certificate_id UUID REFERENCES certificates(id) ON DELETE CASCADE,
    device_id TEXT NOT NULL,
    wipe_passes INTEGER DEFAULT 1,
    bytes_wiped BIGINT,
    duration_seconds INTEGER,
    errors TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Verification Logs (track public verifications)
CREATE TABLE verification_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cert_id TEXT,
    verification_result TEXT NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to certificates table
CREATE TRIGGER update_certificates_updated_at
    BEFORE UPDATE ON certificates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to user_profiles table
CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();