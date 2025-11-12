-- Enable Row Level Security on all tables
ALTER TABLE certificates ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE wipe_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE verification_logs ENABLE ROW LEVEL SECURITY;

-- Certificates Policies
-- Users can view their own certificates
CREATE POLICY "Users can view own certificates"
    ON certificates FOR SELECT
    USING (auth.uid() = user_id);

-- Users can insert their own certificates
CREATE POLICY "Users can insert own certificates"
    ON certificates FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Users can update their own certificates
CREATE POLICY "Users can update own certificates"
    ON certificates FOR UPDATE
    USING (auth.uid() = user_id);

-- Users can delete their own certificates
CREATE POLICY "Users can delete own certificates"
    ON certificates FOR DELETE
    USING (auth.uid() = user_id);

-- Public read access for verification (by cert_id only)
CREATE POLICY "Public can verify certificates"
    ON certificates FOR SELECT
    USING (true);

-- User Profiles Policies
CREATE POLICY "Users can view own profile"
    ON user_profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile"
    ON user_profiles FOR INSERT
    WITH CHECK (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON user_profiles FOR UPDATE
    USING (auth.uid() = id);

-- Wipe Logs Policies
CREATE POLICY "Users can view own wipe logs"
    ON wipe_logs FOR SELECT
    USING (
        certificate_id IN (
            SELECT id FROM certificates WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert own wipe logs"
    ON wipe_logs FOR INSERT
    WITH CHECK (
        certificate_id IN (
            SELECT id FROM certificates WHERE user_id = auth.uid()
        )
    );

-- Verification Logs Policies (public can insert for tracking)
CREATE POLICY "Public can insert verification logs"
    ON verification_logs FOR INSERT
    WITH CHECK (true);

-- Service role can view all verification logs
CREATE POLICY "Service role can view all verification logs"
    ON verification_logs FOR SELECT
    USING (auth.jwt() ->> 'role' = 'service_role');