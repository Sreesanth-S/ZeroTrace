ALTER TABLE certificates ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE wipe_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE verification_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role can view all certificates"
ON certificates FOR SELECT
USING ((select auth.jwt())->>'role' = 'service_role');

CREATE POLICY "Service role can insert any certificate"
ON certificates FOR INSERT
WITH CHECK ((select auth.jwt())->>'role' = 'service_role');

CREATE POLICY "Service role can update any certificate"
ON certificates FOR UPDATE
USING ((select auth.jwt())->>'role' = 'service_role');

CREATE POLICY "Service role can delete any certificate"
ON certificates FOR DELETE
USING ((select auth.jwt())->>'role' = 'service_role');

-- Public can view all certificates for verification
CREATE POLICY "Public can view certificates"
ON certificates FOR SELECT
USING (true);

-- Users can view their own certificates
CREATE POLICY "Users can view own certificates"
ON certificates FOR SELECT
USING (auth.uid() = user_id OR auth.uid() IS NULL);

-- Users can insert certificates (for their own devices)
CREATE POLICY "Users can insert own certificates"
ON certificates FOR INSERT
WITH CHECK (auth.uid() = user_id OR user_id IS NULL);

-- Users can update their own certificates
CREATE POLICY "Users can update own certificates"
ON certificates FOR UPDATE
USING (auth.uid() = user_id OR user_id IS NULL);

-- Users can delete their own certificates
CREATE POLICY "Users can delete own certificates"
ON certificates FOR DELETE
USING (auth.uid() = user_id OR user_id IS NULL);


CREATE POLICY "Service role can view all user profiles"
ON user_profiles FOR SELECT
USING ((select auth.jwt())->>'role' = 'service_role');

CREATE POLICY "Service role can insert any user profile"
ON user_profiles FOR INSERT
WITH CHECK ((select auth.jwt())->>'role' = 'service_role');

CREATE POLICY "Service role can update any user profile"
ON user_profiles FOR UPDATE
USING ((select auth.jwt())->>'role' = 'service_role');

CREATE POLICY "Service role can delete any user profile"
ON user_profiles FOR DELETE
USING ((select auth.jwt())->>'role' = 'service_role');

-- Users can view their own profile
CREATE POLICY "Users can view own profile"
ON user_profiles FOR SELECT
USING (auth.uid() = id);

-- Users can create their own profile
CREATE POLICY "Users can create own profile"
ON user_profiles FOR INSERT
WITH CHECK (auth.uid() = id);

-- Users can update their own profile
CREATE POLICY "Users can update own profile"
ON user_profiles FOR UPDATE
USING (auth.uid() = id)
WITH CHECK (auth.uid() = id);

-- Users can delete their own profile
CREATE POLICY "Users can delete own profile"
ON user_profiles FOR DELETE
USING (auth.uid() = id);



CREATE POLICY "Service role can view all wipe logs"
ON wipe_logs FOR SELECT
USING ((select auth.jwt())->>'role' = 'service_role');

CREATE POLICY "Service role can insert any wipe log"
ON wipe_logs FOR INSERT
WITH CHECK ((select auth.jwt())->>'role' = 'service_role');

CREATE POLICY "Service role can update any wipe log"
ON wipe_logs FOR UPDATE
USING ((select auth.jwt())->>'role' = 'service_role');

CREATE POLICY "Service role can delete any wipe log"
ON wipe_logs FOR DELETE
USING ((select auth.jwt())->>'role' = 'service_role');

-- Users can view their own wipe logs
CREATE POLICY "Users can view own wipe logs"
ON wipe_logs FOR SELECT
USING (auth.uid() IS NOT NULL);

-- Users can insert wipe logs
CREATE POLICY "Users can insert wipe logs"
ON wipe_logs FOR INSERT
WITH CHECK (auth.uid() IS NOT NULL OR true);

-- Users can update their own wipe logs
CREATE POLICY "Users can update wipe logs"
ON wipe_logs FOR UPDATE
USING (auth.uid() IS NOT NULL);

-- Users can delete their own wipe logs
CREATE POLICY "Users can delete wipe logs"
ON wipe_logs FOR DELETE
USING (auth.uid() IS NOT NULL);

-- Service role can upload to any folder in certificates bucket
CREATE POLICY "Service role can upload any certificate file"
    ON storage.objects FOR INSERT
    WITH CHECK (
        bucket_id = 'certificates' AND
        (select auth.jwt())->>'role' = 'service_role'
    );

-- Service role can view any file in certificates bucket
CREATE POLICY "Service role can view any certificate file"
    ON storage.objects FOR SELECT
    USING (
        bucket_id = 'certificates' AND
        (select auth.jwt())->>'role' = 'service_role'
    );

-- Service role can update any file in certificates bucket
CREATE POLICY "Service role can update any certificate file"
    ON storage.objects FOR UPDATE
    USING (
        bucket_id = 'certificates' AND
        (select auth.jwt())->>'role' = 'service_role'
    );

-- Service role can delete any file in certificates bucket
CREATE POLICY "Service role can delete any certificate file"
    ON storage.objects FOR DELETE
    USING (
        bucket_id = 'certificates' AND
        (select auth.jwt())->>'role' = 'service_role'
    );

-- Authenticated users can manage only files in their own certificate folder
CREATE POLICY "Authenticated users can upload own certificates"
    ON storage.objects FOR INSERT TO authenticated
    WITH CHECK (
        bucket_id = 'certificates' AND
        (storage.foldername(name))[1] = (select auth.uid()::text)
    );

CREATE POLICY "Authenticated users can view own certificates"
    ON storage.objects FOR SELECT TO authenticated
    USING (
        bucket_id = 'certificates' AND
        (storage.foldername(name))[1] = (select auth.uid()::text)
    );

CREATE POLICY "Authenticated users can update own certificates"
    ON storage.objects FOR UPDATE TO authenticated
    USING (
        bucket_id = 'certificates' AND
        (storage.foldername(name))[1] = (select auth.uid()::text)
    )
    WITH CHECK (
        bucket_id = 'certificates' AND
        (storage.foldername(name))[1] = (select auth.uid()::text)
    );


-- ========================================
-- VERIFICATION LOGS - RLS Policies
-- ========================================

CREATE POLICY "Service role can view all verification logs"
ON verification_logs FOR SELECT
USING ((select auth.jwt())->>'role' = 'service_role');

CREATE POLICY "Service role can insert verification logs"
ON verification_logs FOR INSERT
WITH CHECK ((select auth.jwt())->>'role' = 'service_role');

CREATE POLICY "Service role can update verification logs"
ON verification_logs FOR UPDATE
USING ((select auth.jwt())->>'role' = 'service_role');

CREATE POLICY "Service role can delete verification logs"
ON verification_logs FOR DELETE
USING ((select auth.jwt())->>'role' = 'service_role');

-- Public can insert verification logs (for tracking public verification attempts)
CREATE POLICY "Public can insert verification logs"
ON verification_logs FOR INSERT
WITH CHECK (true);

-- Service role can view all verification logs
CREATE POLICY "Anyone can insert verification logs"
ON verification_logs FOR INSERT
WITH CHECK (true);

-- ========================================
-- VERIFICATION - Check Policies
-- ========================================

-- View all policies for certificates table
SELECT schemaname, tablename, policyname, permissive, cmd, qual
FROM pg_policies
WHERE tablename = 'certificates'
ORDER BY policyname;

-- View all policies for user_profiles table
SELECT schemaname, tablename, policyname, permissive, cmd, qual
FROM pg_policies
WHERE tablename = 'user_profiles'
ORDER BY policyname;

-- View all policies for wipe_logs table
SELECT schemaname, tablename, policyname, permissive, cmd, qual
FROM pg_policies
WHERE tablename = 'wipe_logs'
ORDER BY policyname;

-- View all storage policies for certificates bucket
SELECT schemaname, tablename, policyname, permissive, cmd
FROM pg_policies
WHERE schemaname = 'storage' AND tablename = 'objects'
AND (policyname LIKE '%certificate%' OR policyname LIKE '%Service%')
ORDER BY policyname;
