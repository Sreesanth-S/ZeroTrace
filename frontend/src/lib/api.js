// ============================================================================
// ZeroTrace Frontend API Client
// Connects exclusively to the authoritative FastAPI backend (VITE_API_URL).
// All authentication, token storage, and business logic route through FastAPI.
// ============================================================================

export const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

const TOKEN_KEY = "zerotrace_token";
const USER_KEY = "zerotrace_user";
const REFRESH_KEY = "zerotrace_refresh_token";

export const authStorage = {
  getToken: () => localStorage.getItem(TOKEN_KEY),
  getUser: () => {
    try {
      const u = localStorage.getItem(USER_KEY);
      return u ? JSON.parse(u) : null;
    } catch {
      return null;
    }
  },
  getRefreshToken: () => localStorage.getItem(REFRESH_KEY),
  setSession: (authData) => {
    if (authData?.access_token) {
      localStorage.setItem(TOKEN_KEY, authData.access_token);
    }
    if (authData?.user) {
      localStorage.setItem(USER_KEY, JSON.stringify(authData.user));
    }
    if (authData?.refresh_token) {
      localStorage.setItem(REFRESH_KEY, authData.refresh_token);
    }
    window.dispatchEvent(new Event("zerotrace-auth-change"));
  },
  clearSession: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem(REFRESH_KEY);
    window.dispatchEvent(new Event("zerotrace-auth-change"));
  },
};

// Generic fetch wrapper with automatic JWT authorization header
async function request(endpoint, options = {}) {
  const url = `${API_URL}${endpoint}`;
  const token = authStorage.getToken();

  const headers = {
    ...options.headers,
  };

  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = headers["Content-Type"] || "application/json";
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  // Handle 401 Unauthorized (expired token)
  if (response.status === 401) {
    const errorData = await response.json().catch(() => ({}));
    authStorage.clearSession();
    throw new Error(errorData.detail || errorData.message || "Session expired. Please sign in again.");
  }

  return response;
}

export const api = {
  // --- Authentication ---
  async login(email, password) {
    const res = await fetch(`${API_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || data.message || "Login failed. Verify credentials.");
    }

    authStorage.setSession(data);
    return data;
  },

  async register(email, password, fullName) {
    const res = await fetch(`${API_URL}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, full_name: fullName }),
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || data.message || "Registration failed.");
    }

    if (data.access_token) {
      authStorage.setSession(data);
    }
    return data;
  },

  async logout() {
    authStorage.clearSession();
  },

  async forgotPassword(email) {
    const res = await fetch(`${API_URL}/auth/forgot-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || data.message || "Failed to send recovery link.");
    }
    return data;
  },

  async resetPassword(password) {
    const res = await request("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ password }),
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || data.message || "Failed to update password.");
    }
    return data;
  },

  async getProfile() {
    const res = await request("/auth/me");
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || data.message || "Failed to fetch profile.");
    }
    return data;
  },

  async updateProfile(updates) {
    const res = await request("/auth/profile", {
      method: "PATCH",
      body: JSON.stringify(updates),
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || data.message || "Failed to update profile.");
    }
    return data;
  },

  async deleteAccount() {
    const res = await request("/auth/account/delete", {
      method: "POST",
      body: JSON.stringify({ confirmation: "DELETE MY ACCOUNT" }),
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || data.message || "Failed to delete account.");
    }

    authStorage.clearSession();
    return data;
  },

  // --- Certificates ---
  async getCertificates() {
    const res = await request("/certificates?limit=100");
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || data.message || "Failed to fetch certificates.");
    }
    return data;
  },

  async revokeCertificate(certId, reason) {
    const res = await request(`/certificates/${certId}/revoke`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || data.message || "Failed to revoke certificate.");
    }
    return data;
  },

  // --- Verification ---
  async verifyPdf(formData) {
    const res = await fetch(`${API_URL}/verify/pdf`, {
      method: "POST",
      body: formData,
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || data.message || "Verification request failed.");
    }
    return data;
  },
};
