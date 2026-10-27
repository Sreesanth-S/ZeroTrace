-- Apply this migration to an existing Supabase project.
ALTER TABLE public.user_profiles
    ADD COLUMN IF NOT EXISTS pin_hash TEXT;

ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own profile" ON public.user_profiles;
CREATE POLICY "Users can view own profile"
ON public.user_profiles FOR SELECT
USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can create own profile" ON public.user_profiles;
CREATE POLICY "Users can create own profile"
ON public.user_profiles FOR INSERT
WITH CHECK (auth.uid() = id);

DROP POLICY IF EXISTS "Users can update own profile" ON public.user_profiles;
CREATE POLICY "Users can update own profile"
ON public.user_profiles FOR UPDATE
USING (auth.uid() = id)
WITH CHECK (auth.uid() = id);

CREATE OR REPLACE FUNCTION public.handle_new_user_profile()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    INSERT INTO public.user_profiles (id, full_name)
    VALUES (
        NEW.id,
        COALESCE(
            NEW.raw_user_meta_data->>'full_name',
            NEW.raw_user_meta_data->>'name',
            SPLIT_PART(NEW.email, '@', 1),
            ''
        )
    )
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user_profile();

-- Retroactively populate user_profiles for any existing users in auth.users
INSERT INTO public.user_profiles (id, full_name)
SELECT 
    id, 
    COALESCE(
        raw_user_meta_data->>'full_name', 
        raw_user_meta_data->>'name', 
        SPLIT_PART(email, '@', 1), 
        ''
    )
FROM auth.users
ON CONFLICT (id) DO NOTHING;


-- Allow the desktop client to manage only files in its own user folder.
DROP POLICY IF EXISTS "Authenticated users can upload own certificates" ON storage.objects;
CREATE POLICY "Authenticated users can upload own certificates"
ON storage.objects FOR INSERT TO authenticated
WITH CHECK (
    bucket_id = 'certificates'
    AND (storage.foldername(name))[1] = (select auth.uid()::text)
);

DROP POLICY IF EXISTS "Authenticated users can view own certificates" ON storage.objects;
CREATE POLICY "Authenticated users can view own certificates"
ON storage.objects FOR SELECT TO authenticated
USING (
    bucket_id = 'certificates'
    AND (storage.foldername(name))[1] = (select auth.uid()::text)
);

DROP POLICY IF EXISTS "Authenticated users can update own certificates" ON storage.objects;
CREATE POLICY "Authenticated users can update own certificates"
ON storage.objects FOR UPDATE TO authenticated
USING (
    bucket_id = 'certificates'
    AND (storage.foldername(name))[1] = (select auth.uid()::text)
)
WITH CHECK (
    bucket_id = 'certificates'
    AND (storage.foldername(name))[1] = (select auth.uid()::text)
);
