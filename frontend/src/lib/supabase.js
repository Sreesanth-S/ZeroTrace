// ============================================================================
// Deprecated compatibility shim.
// All operations have been migrated to the authoritative FastAPI backend client (api.js).
// No Supabase URL or Anon Key is required.
// ============================================================================

import { api, authStorage } from './api';

export const supabase = {
  auth: {
    signInWithPassword: ({ email, password }) => api.login(email, password),
    signUp: ({ email, password, options }) => api.register(email, password, options?.data?.full_name),
    signOut: () => api.logout(),
    getUser: async () => ({ data: { user: authStorage.getUser() }, error: null }),
    getSession: async () => {
      const token = authStorage.getToken();
      const user = authStorage.getUser();
      return { data: { session: token ? { access_token: token, user } : null }, error: null };
    },
  },
};

export default supabase;
