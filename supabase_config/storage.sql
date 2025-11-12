-- Create certificates storage bucket
-- Run this in Supabase Dashboard > Storage or via API

-- Storage bucket policies for certificates
-- Users can upload to their own folder
INSERT INTO storage.buckets (id, name, public)
VALUES ('certificates', 'certificates', false);

-- Policy: Users can upload to their own folder
CREATE POLICY "Users can upload own certificates"
    ON storage.objects FOR INSERT
    WITH CHECK (
        bucket_id = 'certificates' AND
        auth.uid()::text = (storage.foldername(name))[1]
    );

-- Policy: Users can view their own certificates
CREATE POLICY "Users can view own certificates"
    ON storage.objects FOR SELECT
    USING (
        bucket_id = 'certificates' AND
        auth.uid()::text = (storage.foldername(name))[1]
    );

-- Policy: Users can update their own certificates
CREATE POLICY "Users can update own certificates"
    ON storage.objects FOR UPDATE
    USING (
        bucket_id = 'certificates' AND
        auth.uid()::text = (storage.foldername(name))[1]
    );

-- Policy: Users can delete their own certificates
CREATE POLICY "Users can delete own certificates"
    ON storage.objects FOR DELETE
    USING (
        bucket_id = 'certificates' AND
        auth.uid()::text = (storage.foldername(name))[1]
    );

-- Policy: Public can read certificates for verification
-- (Consider making this more restrictive based on your needs)
CREATE POLICY "Public can view certificates for verification"
    ON storage.objects FOR SELECT
    USING (bucket_id = 'certificates');