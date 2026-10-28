import React, { useEffect, useMemo, useState } from "react";
import { api, authStorage, API_URL } from "./lib/api";

const apiUrl = API_URL;

// ---------------------------------------------------------------------------
// Custom Auth Hook (Backend Authoritative Session)
// ---------------------------------------------------------------------------
function useAuth() {
  const [user, setUser] = useState(() => authStorage.getUser());
  const [session, setSession] = useState(() => {
    const token = authStorage.getToken();
    const u = authStorage.getUser();
    return token ? { access_token: token, user: u } : null;
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const handleAuthChange = () => {
      const token = authStorage.getToken();
      const u = authStorage.getUser();
      setUser(u);
      setSession(token ? { access_token: token, user: u } : null);
    };

    window.addEventListener("zerotrace-auth-change", handleAuthChange);
    return () => window.removeEventListener("zerotrace-auth-change", handleAuthChange);
  }, []);

  return { user, session, loading };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function formatBytes(bytes) {
  if (!bytes || isNaN(bytes)) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB", "TB", "PB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

function formatDate(isoStr) {
  if (!isoStr) return "N/A";
  try {
    return new Date(isoStr).toLocaleString();
  } catch {
    return isoStr;
  }
}

// ---------------------------------------------------------------------------
// Top Navigation Bar
// ---------------------------------------------------------------------------
function Navbar({ view, setView, user, onLogout }) {
  const isAuthenticated = Boolean(user);

  return (
    <header className="navbar">
      <div className="navbar-inner">
        <button
          className="brand-badge"
          onClick={() => setView(isAuthenticated ? "dashboard" : "home")}
          type="button"
          id="nav-brand-logo"
        >
          <div className="brand-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#F8FAFC" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              <path d="m9 12 2 2 4-4" />
            </svg>
          </div>
          <div style={{ textAlign: "left" }}>
            <span className="brand-name">
              <span>Zero</span>Trace
            </span>
            <span className="brand-tag" style={{ marginLeft: "8px" }}>
              Enterprise
            </span>
          </div>
        </button>

        <nav className="nav-links">
          <button
            className={`nav-btn ${view === "public" ? "active" : ""}`}
            onClick={() => setView("public")}
            type="button"
            id="nav-public-verify"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" />
              <path d="m21 21-4.3-4.3" />
            </svg>
            Verify Certificate
          </button>

          {isAuthenticated ? (
            <>
              <button
                className={`nav-btn ${view === "dashboard" ? "active" : ""}`}
                onClick={() => setView("dashboard")}
                type="button"
                id="nav-my-certs"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="16" y1="13" x2="8" y2="13" />
                  <line x1="16" y1="17" x2="8" y2="17" />
                  <polyline points="10 9 9 9 8 9" />
                </svg>
                My Certificates
              </button>

              <button
                className={`nav-btn ${view === "profile" ? "active" : ""}`}
                onClick={() => setView("profile")}
                type="button"
                id="nav-account-profile"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
                Profile
              </button>

              <button
                className="nav-btn logout"
                onClick={onLogout}
                type="button"
                id="nav-logout-btn"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                  <polyline points="16 17 21 12 16 7" />
                  <line x1="21" y1="12" x2="9" y2="12" />
                </svg>
                Logout
              </button>
            </>
          ) : (
            <>
              <button
                className={`nav-btn ${view === "login" ? "active" : ""}`}
                onClick={() => setView("login")}
                type="button"
                id="nav-login-btn"
              >
                Login
              </button>
              <button
                className="nav-btn primary"
                onClick={() => setView("register")}
                type="button"
                id="nav-register-btn"
              >
                Create Account
              </button>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}

// ---------------------------------------------------------------------------
// Landing Hero View
// ---------------------------------------------------------------------------
function HomeScreen({ setView }) {
  return (
    <div className="animate-fade">
      <div className="hero-box">
        <div className="hero-pill">
          <span style={{ display: "inline-block", width: 6, height: 6, borderRadius: "50%", background: "#38BDF8" }} />
          ZeroTrace Enterprise Cryptographic Verification Engine
        </div>
        <h1 className="hero-title">
          Authoritative Device Wiping & <span className="gradient-text">Dual-Anchor Verification</span>
        </h1>
        <p className="hero-subtitle">
          Cryptographically signed sanitization compliance (NIST 800-88, DoD 5220.22-M). 
          Validate certificate authenticity against immutable authoritative registry records and pinned ECDSA signatures.
        </p>

        <div className="hero-actions">
          <button
            className="btn btn-primary"
            style={{ padding: "14px 32px", fontSize: "1.05rem" }}
            onClick={() => setView("public")}
            type="button"
            id="hero-verify-btn"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" />
              <path d="m21 21-4.3-4.3" />
            </svg>
            Verify a Certificate Now
          </button>
          <button
            className="btn btn-secondary"
            style={{ padding: "14px 28px", fontSize: "1.05rem" }}
            onClick={() => setView("login")}
            type="button"
            id="hero-login-btn"
          >
            Sign In to Dashboard
          </button>
        </div>
      </div>

      <div className="features-grid">
        <div className="feature-card">
          <div className="feature-icon-wrapper">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              <path d="m9 12 2 2 4-4" />
            </svg>
          </div>
          <h3 className="feature-title">Dual-Anchor Verification</h3>
          <p className="feature-desc">
            Independent two-tier validation combines ECDSA-SHA256 mathematical proof with authoritative PostgreSQL cloud registry records.
          </p>
        </div>

        <div className="feature-card">
          <div className="feature-icon-wrapper">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
              <line x1="8" y1="21" x2="16" y2="21" />
              <line x1="12" y1="17" x2="12" y2="21" />
            </svg>
          </div>
          <h3 className="feature-title">Media-Aware Standards</h3>
          <p className="feature-desc">
            Compliant with NIST 800-88 Rev 1 (Clear/Purge) & DoD 5220.22-M with custom tailored overwrite algorithms for NVMe, SSD, and HDD.
          </p>
        </div>

        <div className="feature-card">
          <div className="feature-icon-wrapper">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
          </div>
          <h3 className="feature-title">Hardware Security PIN</h3>
          <p className="feature-desc">
            Server-side bcrypt salted PIN protection synchronizes seamlessly between desktop wiping stations and compliance portals.
          </p>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Public Verification Portal
// ---------------------------------------------------------------------------
function PublicVerificationPortal({ setView }) {
  const [uploadedFileName, setUploadedFileName] = useState("");
  const [verificationResult, setVerificationResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const verifyByFile = async (file) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setVerificationResult({
        success: false,
        final_verdict: "Unverified",
        verdict_explanation: "Only official ZeroTrace PDF certificates (.pdf) are supported for tamper detection.",
      });
      return;
    }
    setUploadedFileName(file.name);
    setVerificationResult(null);
    setLoading(true);

    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch(`${apiUrl}/verify/pdf`, {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      setVerificationResult(data);
    } catch {
      setVerificationResult({
        success: false,
        final_verdict: "Unverified",
        verdict_explanation: "Could not upload certificate for verification.",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) verifyByFile(file);
  };

  const getVerdictClass = (verdict) => {
    switch (verdict?.toLowerCase()) {
      case "verified":
        return "verified";
      case "revoked":
        return "revoked";
      case "tampered":
        return "tampered";
      default:
        return "unverified";
    }
  };

  return (
    <div className="glass-panel animate-fade" style={{ maxWidth: 860, margin: "0 auto" }}>
      <div style={{ textAlign: "center", marginBottom: 24 }}>
        <h2 style={{ fontFamily: "var(--font-display)", fontSize: "1.85rem", fontWeight: 800, color: "var(--text-pure)" }}>
          PDF Certificate Verification & Tamper Detection
        </h2>
        <p style={{ color: "var(--text-mid)", fontSize: "0.95rem", marginTop: 6 }}>
          Upload an official ZeroTrace PDF certificate to cryptographically verify its digital signature and detect any data tampering.
        </p>
      </div>

      <div
        className="dropzone"
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => document.getElementById("certificate-file-input")?.click()}
        style={{ borderColor: dragOver ? "var(--cyan-primary)" : undefined, cursor: "pointer" }}
      >
        <input
          type="file"
          id="certificate-file-input"
          accept=".pdf"
          onChange={(e) => verifyByFile(e.target.files?.[0])}
          style={{ display: "none" }}
        />
        <div className="dropzone-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" style={{ margin: "0 auto" }}>
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="12" y1="18" x2="12" y2="12" />
            <line x1="9" y1="15" x2="15" y2="15" />
          </svg>
        </div>
        <h4 style={{ fontSize: "1.05rem", fontWeight: 700, color: "var(--text-pure)", marginBottom: 6 }}>
          {uploadedFileName || "Click or drag certificate PDF file here"}
        </h4>
        <p style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
          Accepts authentic ZeroTrace digitally signed PDF certificates (.pdf) to verify cryptographic authenticity and detect tampering.
        </p>
      </div>

      {loading && (
        <div style={{ textAlign: "center", padding: "30px 0" }}>
          <div style={{ display: "inline-block", width: 28, height: 28, border: "3px solid rgba(56, 189, 248, 0.2)", borderTopColor: "var(--cyan-primary)", borderRadius: "50%", animation: "spin 1s linear infinite" }} />
          <p style={{ marginTop: 12, fontSize: "0.9rem", color: "var(--text-mid)" }}>
            Extracting cryptographic payload and auditing document integrity...
          </p>
          <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
        </div>
      )}

      {/* Verification Result Output */}
      {verificationResult && !loading && (
        <div className={`verdict-banner ${getVerdictClass(verificationResult.final_verdict)}`}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
            <div>
              <span className={`badge badge-${getVerdictClass(verificationResult.final_verdict)}`} style={{ fontSize: "0.85rem", padding: "4px 12px" }}>
                {verificationResult.final_verdict || "Unverified"}
              </span>
            </div>
            <span style={{ fontSize: "0.85rem", color: "var(--text-mid)", fontFamily: "var(--font-mono)" }}>
              {verificationResult.success ? "✓ Cryptographic Proof Valid" : "✗ Trust Incomplete"}
            </span>
          </div>

          <h3 style={{ fontSize: "1.15rem", fontWeight: 700, color: "var(--text-pure)", marginTop: 14, marginBottom: 8 }}>
            {verificationResult.verdict_explanation || "No explanation recorded."}
          </h3>

          {/* 4-Check Inspection Cards */}
          <div className="checks-grid">
            <div className="check-item">
              <span className="check-label">1. Cryptographic Signature</span>
              <span className={`check-status ${verificationResult.cryptographic_authenticity ? "passed" : "failed"}`}>
                {verificationResult.cryptographic_authenticity ? "✓ Valid Authoritative ECDSA" : "✗ Invalid / Mismatched"}
              </span>
              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                Authoritative elliptic curve P-256 signature
              </span>
            </div>

            <div className="check-item">
              <span className="check-label">2. Registry Recognition</span>
              <span className={`check-status ${verificationResult.registry_recognition ? "passed" : "failed"}`}>
                {verificationResult.registry_recognition ? "✓ Confirmed in Database" : "✗ Not Found"}
              </span>
              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                PostgreSQL immutable certificate record
              </span>
            </div>

            <div className="check-item">
              <span className="check-label">3. Revocation State</span>
              <span className={`check-status ${verificationResult.revocation_status === "active" ? "passed" : verificationResult.revocation_status === "revoked" ? "warning" : "failed"}`}>
                {verificationResult.revocation_status === "active" ? "✓ Active (Valid)" : verificationResult.revocation_status === "revoked" ? "⚠️ Revoked" : "Unknown"}
              </span>
              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                Auditable revocation registry status
              </span>
            </div>

            <div className="check-item">
              <span className="check-label">4. Issuer Account</span>
              <span className={`check-status ${verificationResult.issuer_account_status === "active" ? "passed" : "warning"}`}>
                {verificationResult.issuer_account_status === "active" ? "✓ Active Account" : verificationResult.issuer_account_status === "deleted" ? "ℹ️ Preserved (Soft-Deleted)" : verificationResult.issuer_account_status || "Unregistered"}
              </span>
              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                Compliance trail preservation
              </span>
            </div>
          </div>

          {/* Detailed Certificate Metadata Accordion */}
          {verificationResult.certificate && (
            <div style={{ marginTop: 20, paddingTop: 16, borderTop: "1px solid var(--border-card)" }}>
              <h4 style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--text-pure)", marginBottom: 12 }}>
                Certificate Record Details
              </h4>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12, fontSize: "0.85rem" }}>
                <div>
                  <span style={{ color: "var(--text-muted)", display: "block" }}>Certificate ID</span>
                  <strong className="mono" style={{ color: "var(--cyan-primary)" }}>{verificationResult.certificate.cert_id}</strong>
                </div>
                <div>
                  <span style={{ color: "var(--text-muted)", display: "block" }}>Device Target</span>
                  <strong>{verificationResult.certificate.device_name || "Device"} ({verificationResult.certificate.media_type || "Drive"})</strong>
                </div>
                <div>
                  <span style={{ color: "var(--text-muted)", display: "block" }}>Wipe Method</span>
                  <strong>{verificationResult.certificate.wipe_method || "N/A"}</strong>
                </div>
                <div>
                  <span style={{ color: "var(--text-muted)", display: "block" }}>Sanitization Standard</span>
                  <span className="badge badge-verified" style={{ fontSize: "0.7rem", marginTop: 2 }}>
                    {verificationResult.certificate.sanitization_level || "Purge"}
                  </span>
                </div>
                <div>
                  <span style={{ color: "var(--text-muted)", display: "block" }}>Bytes Wiped</span>
                  <strong>{formatBytes(verificationResult.certificate.bytes_wiped)}</strong>
                </div>
                <div>
                  <span style={{ color: "var(--text-muted)", display: "block" }}>Issued Timestamp</span>
                  <span>{formatDate(verificationResult.certificate.issued_at)}</span>
                </div>
              </div>

              {verificationResult.certificate.revocation_reason && (
                <div style={{ marginTop: 12, padding: 10, background: "rgba(245, 158, 11, 0.1)", border: "1px solid rgba(245, 158, 11, 0.3)", borderRadius: 8, fontSize: "0.85rem", color: "#FDE68A" }}>
                  <strong>Revocation Reason:</strong> {verificationResult.certificate.revocation_reason}
                  {verificationResult.certificate.revoked_at && <span> (Revoked on {formatDate(verificationResult.certificate.revoked_at)})</span>}
                </div>
              )}

              <div style={{ marginTop: 16 }}>
                <a
                  href={`${apiUrl}/certificates/${verificationResult.certificate.cert_id}/download`}
                  target="_blank"
                  rel="noreferrer"
                  className="btn btn-primary btn-sm"
                  id="btn-download-verified-pdf"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="7 10 12 15 17 10" />
                    <line x1="12" y1="15" x2="12" y2="3" />
                  </svg>
                  Download Signed Compliance PDF
                </a>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// User Certificates Dashboard (My Certificates)
// ---------------------------------------------------------------------------
function UserDashboard({ user, session }) {
  const [certificates, setCertificates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  // Revocation modal state
  const [revokingCert, setRevokingCert] = useState(null);
  const [revocationReason, setRevocationReason] = useState("");
  const [revoking, setRevoking] = useState(false);
  const [revocationError, setRevocationError] = useState("");

  // Detailed inspect modal state
  const [inspectCert, setInspectCert] = useState(null);

  const fetchCertificates = async () => {
    try {
      setLoading(true);
      const token = session?.access_token;
      if (!token) return;

      const response = await fetch(`${apiUrl}/certificates?limit=100`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const res = await response.json();
        setCertificates(res.certificates || []);
      } else {
        setCertificates([]);
      }
    } catch {
      setCertificates([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCertificates();
  }, [user, session]);

  const handleRevokeSubmit = async (e) => {
    e.preventDefault();
    if (!revokingCert || !revocationReason.trim()) return;

    setRevoking(true);
    setRevocationError("");

    try {
      const token = session?.access_token;
      const response = await fetch(`${apiUrl}/certificates/${revokingCert.cert_id}/revoke`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ reason: revocationReason.trim() }),
      });

      if (response.ok) {
        setRevokingCert(null);
        setRevocationReason("");
        await fetchCertificates();
      } else {
        const err = await response.json();
        setRevocationError(err.message || "Failed to revoke certificate.");
      }
    } catch (err) {
      setRevocationError(err.message || "Network error occurred.");
    } finally {
      setRevoking(false);
    }
  };

  const filteredCerts = useMemo(() => {
    return certificates.filter((cert) => {
      const matchesSearch =
        (cert.cert_id || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
        (cert.device_name || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
        (cert.wipe_method || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
        (cert.media_type || "").toLowerCase().includes(searchTerm.toLowerCase());

      const status = (cert.status || "verified").toLowerCase();
      const matchesStatus =
        statusFilter === "all" ||
        (statusFilter === "verified" && status === "verified") ||
        (statusFilter === "revoked" && status === "revoked");

      return matchesSearch && matchesStatus;
    });
  }, [certificates, searchTerm, statusFilter]);

  const totalBytes = useMemo(() => {
    return certificates.reduce((acc, c) => acc + (Number(c.bytes_wiped) || 0), 0);
  }, [certificates]);

  return (
    <div className="animate-fade">
      {/* Metrics Banner */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16, marginBottom: 28 }}>
        <div className="glass-panel" style={{ padding: "18px 22px" }}>
          <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>
            Total Certificates
          </span>
          <div style={{ fontSize: "1.8rem", fontWeight: 800, color: "var(--cyan-primary)", marginTop: 4 }}>
            {certificates.length}
          </div>
        </div>

        <div className="glass-panel" style={{ padding: "18px 22px" }}>
          <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>
            Active / Verified
          </span>
          <div style={{ fontSize: "1.8rem", fontWeight: 800, color: "#34D399", marginTop: 4 }}>
            {certificates.filter((c) => (c.status || "verified").toLowerCase() === "verified").length}
          </div>
        </div>

        <div className="glass-panel" style={{ padding: "18px 22px" }}>
          <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>
            Revoked
          </span>
          <div style={{ fontSize: "1.8rem", fontWeight: 800, color: "#FBBF24", marginTop: 4 }}>
            {certificates.filter((c) => (c.status || "").toLowerCase() === "revoked").length}
          </div>
        </div>

        <div className="glass-panel" style={{ padding: "18px 22px" }}>
          <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>
            Total Sanitized Data
          </span>
          <div style={{ fontSize: "1.8rem", fontWeight: 800, color: "var(--text-pure)", marginTop: 4 }}>
            {formatBytes(totalBytes)}
          </div>
        </div>
      </div>

      {/* Main Certificates Card */}
      <div className="glass-panel">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 16, marginBottom: 20 }}>
          <div>
            <h2 style={{ fontFamily: "var(--font-display)", fontSize: "1.45rem", fontWeight: 800, color: "var(--text-pure)" }}>
              Authoritative Certificate Registry
            </h2>
            <p style={{ color: "var(--text-mid)", fontSize: "0.85rem", marginTop: 4 }}>
              Cryptographically verified sanitization records issued to {user.email}
            </p>
          </div>

          <button className="btn btn-secondary btn-sm" onClick={fetchCertificates} type="button">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
            </svg>
            Refresh List
          </button>
        </div>

        {/* Filter Controls */}
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 20 }}>
          <div style={{ flex: 1, minWidth: 240 }}>
            <input
              type="text"
              className="form-input"
              placeholder="Search by Cert ID, Drive Model, Wipe Method..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <select
            className="form-input"
            style={{ width: "auto", minWidth: 160 }}
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">All Statuses</option>
            <option value="verified">Verified Only</option>
            <option value="revoked">Revoked Only</option>
          </select>
        </div>

        {/* Data Table */}
        {loading ? (
          <div style={{ textAlign: "center", padding: "40px 0", color: "var(--text-mid)" }}>
            Loading certificate registry from backend...
          </div>
        ) : filteredCerts.length === 0 ? (
          <div style={{ textAlign: "center", padding: "40px 20px", color: "var(--text-muted)" }}>
            No certificates match your filter criteria.
          </div>
        ) : (
          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Certificate ID</th>
                  <th>Device / Media</th>
                  <th>Method & Standard</th>
                  <th>Issued Date</th>
                  <th>Status</th>
                  <th style={{ textAlign: "right" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredCerts.map((cert) => {
                  const isRevoked = (cert.status || "").toLowerCase() === "revoked";

                  return (
                    <tr key={cert.id || cert.cert_id}>
                      <td>
                        <strong className="mono" style={{ color: "var(--cyan-primary)", fontSize: "0.85rem" }}>
                          {cert.cert_id}
                        </strong>
                      </td>
                      <td>
                        <div style={{ fontWeight: 600, color: "var(--text-pure)" }}>
                          {cert.device_name || "Drive"}
                        </div>
                        <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                          {cert.media_type || "Unknown"} &bull; {formatBytes(cert.bytes_wiped)}
                        </div>
                      </td>
                      <td>
                        <div style={{ color: "var(--text-high)" }}>{cert.wipe_method || "N/A"}</div>
                        <div style={{ fontSize: "0.75rem", color: "var(--cyan-primary)" }}>
                          {cert.sanitization_level || "NIST 800-88"}
                        </div>
                      </td>
                      <td style={{ fontSize: "0.85rem", color: "var(--text-mid)" }}>
                        {formatDate(cert.issued_at)}
                      </td>
                      <td>
                        <span className={`badge ${isRevoked ? "badge-revoked" : "badge-verified"}`}>
                          {isRevoked ? "Revoked" : "Verified"}
                        </span>
                      </td>
                      <td style={{ textAlign: "right" }}>
                        <div style={{ display: "inline-flex", gap: 8, alignItems: "center" }}>
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => setInspectCert(cert)}
                            title="Inspect full details"
                            type="button"
                          >
                            Inspect
                          </button>

                          <a
                            href={`${apiUrl}/certificates/${cert.cert_id}/download`}
                            target="_blank"
                            rel="noreferrer"
                            className="btn btn-primary btn-sm"
                            title="Download Signed PDF"
                          >
                            PDF
                          </a>

                          <a
                            href={`${apiUrl}/certificates/${cert.cert_id}/json`}
                            target="_blank"
                            rel="noreferrer"
                            className="btn btn-secondary btn-sm"
                            title="Download Signed JSON"
                            style={{ padding: "4px 8px", fontSize: "0.75rem" }}
                          >
                            JSON
                          </a>

                          {!isRevoked && (
                            <button
                              className="btn btn-danger btn-sm"
                              onClick={() => {
                                setRevokingCert(cert);
                                setRevocationReason("");
                                setRevocationError("");
                              }}
                              title="Revoke Certificate"
                              type="button"
                            >
                              Revoke
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Revocation Modal */}
      {revokingCert && (
        <div className="modal-overlay" onClick={() => setRevokingCert(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3 className="modal-title" style={{ color: "#F87171" }}>
                Revoke Certificate {revokingCert.cert_id}
              </h3>
              <button className="modal-close" onClick={() => setRevokingCert(null)} type="button">
                &times;
              </button>
            </div>

            <p style={{ fontSize: "0.9rem", color: "var(--text-mid)", lineHeight: 1.5, marginBottom: 16 }}>
              Revocation is an auditable, non-destructive status update. The certificate remains permanently recorded,
              but any verification check will flag it as <strong style={{ color: "#FBBF24" }}>REVOKED</strong>.
            </p>

            {revocationError && (
              <div style={{ padding: 10, background: "rgba(239, 68, 68, 0.15)", border: "1px solid var(--crimson-danger)", borderRadius: 8, color: "#FCA5A5", fontSize: "0.85rem", marginBottom: 14 }}>
                {revocationError}
              </div>
            )}

            <form onSubmit={handleRevokeSubmit}>
              <div className="form-group">
                <label className="form-label">
                  Auditable Revocation Reason <span style={{ color: "#EF4444" }}>*</span>
                </label>
                <textarea
                  className="form-input"
                  rows="3"
                  placeholder="e.g. Device decommissioned, Issued during testing, Physical media discarded..."
                  value={revocationReason}
                  onChange={(e) => setRevocationReason(e.target.value)}
                  required
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 20 }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setRevokingCert(null)}
                  disabled={revoking}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-danger"
                  disabled={revoking || !revocationReason.trim()}
                >
                  {revoking ? "Revoking..." : "Confirm Revocation"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Detailed Inspection Modal */}
      {inspectCert && (
        <div className="modal-overlay" onClick={() => setInspectCert(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3 className="modal-title">
                Certificate Details
              </h3>
              <button className="modal-close" onClick={() => setInspectCert(null)} type="button">
                &times;
              </button>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, fontSize: "0.875rem", marginBottom: 20 }}>
              <div>
                <span style={{ color: "var(--text-muted)", display: "block" }}>Certificate ID</span>
                <strong className="mono" style={{ color: "var(--cyan-primary)" }}>{inspectCert.cert_id}</strong>
              </div>
              <div>
                <span style={{ color: "var(--text-muted)", display: "block" }}>Validation Status</span>
                <span className={`badge ${(inspectCert.validation_status || inspectCert.status || "").toLowerCase() === "revoked" ? "badge-revoked" : "badge-verified"}`}>
                  {inspectCert.validation_status || inspectCert.status || "Verified"}
                </span>
              </div>
              <div>
                <span style={{ color: "var(--text-muted)", display: "block" }}>Device Name</span>
                <strong>{inspectCert.device_name || "Drive"}</strong>
              </div>
              <div>
                <span style={{ color: "var(--text-muted)", display: "block" }}>Media Type</span>
                <strong>{inspectCert.media_type || "N/A"}</strong>
              </div>
              <div>
                <span style={{ color: "var(--text-muted)", display: "block" }}>Wipe Method</span>
                <strong>{inspectCert.wipe_method || "N/A"}</strong>
              </div>
              <div>
                <span style={{ color: "var(--text-muted)", display: "block" }}>Sanitization Level</span>
                <span className={`badge ${(inspectCert.sanitization_level || "").toLowerCase() === "purge" ? "badge-verified" : "badge-pending"}`}>
                  {inspectCert.sanitization_level || "Clear"}
                </span>
              </div>
              <div>
                <span style={{ color: "var(--text-muted)", display: "block" }}>Policy Version</span>
                <strong className="mono">{inspectCert.policy_version || "1.0.0"}</strong>
              </div>
              <div>
                <span style={{ color: "var(--text-muted)", display: "block" }}>Signing Key ID</span>
                <strong className="mono" style={{ fontSize: "0.8rem", wordBreak: "break-all" }}>{inspectCert.signing_key_id || "zerotrace-authoritative-p256-v1"}</strong>
              </div>
              <div>
                <span style={{ color: "var(--text-muted)", display: "block" }}>Bytes Sanitized</span>
                <strong>{formatBytes(inspectCert.bytes_wiped)}</strong>
              </div>
              <div>
                <span style={{ color: "var(--text-muted)", display: "block" }}>Passes Completed</span>
                <strong>{inspectCert.passes || "1"}</strong>
              </div>
              <div style={{ gridColumn: "span 2" }}>
                <span style={{ color: "var(--text-muted)", display: "block" }}>Issued UTC</span>
                <span>{formatDate(inspectCert.issued_at)}</span>
              </div>
              {inspectCert.verification_hash && (
                <div style={{ gridColumn: "span 2" }}>
                  <span style={{ color: "var(--text-muted)", display: "block" }}>Completion Hash (SHA-256)</span>
                  <div className="mono" style={{ fontSize: "0.75rem", wordBreak: "break-all", background: "var(--bg-input)", padding: 8, borderRadius: 6, border: "1px solid var(--border-card)", color: "var(--cyan-primary)" }}>
                    {inspectCert.verification_hash}
                  </div>
                </div>
              )}
              {inspectCert.revoked_at && (
                <div style={{ gridColumn: "span 2", background: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.3)", padding: 12, borderRadius: 8 }}>
                  <div style={{ color: "#F87171", fontWeight: 700, fontSize: "0.85rem" }}>Certificate Revoked</div>
                  <div style={{ fontSize: "0.8rem", color: "var(--text-mid)", marginTop: 2 }}>
                    Revoked At: {formatDate(inspectCert.revoked_at)}
                  </div>
                  {inspectCert.revocation_reason && (
                    <div style={{ fontSize: "0.8rem", color: "var(--text-pure)", marginTop: 2 }}>
                      Reason: {inspectCert.revocation_reason}
                    </div>
                  )}
                </div>
              )}
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, flexWrap: "wrap" }}>
              <a
                href={`${apiUrl}/certificates/${inspectCert.cert_id}/download`}
                target="_blank"
                rel="noreferrer"
                className="btn btn-primary"
              >
                Download Signed PDF
              </a>
              <a
                href={`${apiUrl}/certificates/${inspectCert.cert_id}/json`}
                target="_blank"
                rel="noreferrer"
                className="btn btn-secondary"
              >
                Download Signed JSON
              </a>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setInspectCert(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// User Profile & Account Management
// ---------------------------------------------------------------------------
function ProfileScreen({ user, session, onLogout }) {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);

  // Name editing state
  const [isEditingName, setIsEditingName] = useState(false);
  const [nameInput, setNameInput] = useState("");
  const [updatingName, setUpdatingName] = useState(false);

  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const fetchProfile = async () => {
    try {
      setLoading(true);
      const token = session?.access_token;
      if (!token) return;

      const response = await fetch(`${apiUrl}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setProfile(data);
        setNameInput(data.full_name || user?.user_metadata?.full_name || "");
      }
    } catch {
      // Ignored
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, [session]);

  const handleUpdateName = async (e) => {
    e.preventDefault();
    const cleanName = nameInput.trim();
    if (!cleanName) {
      setError("Name cannot be empty.");
      return;
    }

    setUpdatingName(true);
    setMessage("");
    setError("");

    try {
      const token = session?.access_token;
      // 1. Update backend user_profiles table
      const response = await fetch(`${apiUrl}/auth/profile`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ full_name: cleanName }),
      });



      if (response.ok) {
        setMessage("Name updated successfully!");
        setProfile((prev) => ({ ...prev, full_name: cleanName }));
        setIsEditingName(false);
      } else {
        const err = await response.json();
        setError(err.message || "Failed to update profile name.");
      }
    } catch (err) {
      setError(err.message || "Network error updating name.");
    } finally {
      setUpdatingName(false);
    }
  };

  const handleSoftDelete = async () => {
    const confirmation = window.prompt(
      "To schedule your account for soft-deletion and deactivation, type 'DELETE MY ACCOUNT':\n\n" +
      "(Compliance Note: Your historical sanitization certificates remain preserved for legal auditability)"
    );

    if (confirmation !== "DELETE MY ACCOUNT") {
      alert("Account deletion canceled (confirmation phrase did not match).");
      return;
    }

    setDeleting(true);
    try {
      const token = session?.access_token;
      const response = await fetch(`${apiUrl}/auth/account/delete`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ confirmation }),
      });

      if (response.ok) {
        alert("Your account has been deactivated and marked for soft-deletion. Historical certificates remain preserved.");
        await onLogout();
      } else {
        const err = await response.json();
        alert(`Deletion request failed: ${err.message || "Error"}`);
      }
    } catch (err) {
      alert(`Deletion failed: ${err.message}`);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="glass-panel animate-fade" style={{ maxWidth: 680, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <div>
          <h2 style={{ fontFamily: "var(--font-display)", fontSize: "1.65rem", fontWeight: 800, color: "var(--text-pure)" }}>
            Account Profile
          </h2>
          <p style={{ color: "var(--text-mid)", fontSize: "0.85rem", marginTop: 4 }}>
            ZeroTrace Authoritative Compliance Identity
          </p>
        </div>
        <span className="badge badge-verified">
          Active
        </span>
      </div>

      {message && (
        <div style={{ padding: 12, background: "rgba(16, 185, 129, 0.15)", border: "1px solid var(--emerald-success)", borderRadius: 8, color: "#6EE7B7", fontSize: "0.9rem", marginBottom: 16 }}>
          {message}
        </div>
      )}

      {error && (
        <div style={{ padding: 12, background: "rgba(239, 68, 68, 0.15)", border: "1px solid var(--crimson-danger)", borderRadius: 8, color: "#FCA5A5", fontSize: "0.9rem", marginBottom: 16 }}>
          {error}
        </div>
      )}

      {loading ? (
        <p style={{ color: "var(--text-muted)", padding: "20px 0" }}>Loading account profile...</p>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, fontSize: "0.9rem", marginBottom: 28 }}>
          <div style={{ background: "rgba(11, 19, 43, 0.4)", padding: 14, borderRadius: 10, border: "1px solid var(--border-card)" }}>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Email Address</span>
            <div style={{ fontWeight: 600, color: "var(--text-pure)", marginTop: 4 }}>{user.email}</div>
          </div>

          <div style={{ background: "rgba(11, 19, 43, 0.4)", padding: 14, borderRadius: 10, border: "1px solid var(--border-card)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Full Name</span>
              {!isEditingName && (
                <button
                  type="button"
                  onClick={() => {
                    setNameInput(profile?.full_name || user?.user_metadata?.full_name || "");
                    setIsEditingName(true);
                  }}
                  style={{
                    background: "transparent",
                    border: "none",
                    color: "var(--cyan-primary)",
                    fontSize: "0.75rem",
                    fontWeight: 600,
                    cursor: "pointer",
                    textDecoration: "underline",
                  }}
                  id="btn-edit-name"
                >
                  Edit Name
                </button>
              )}
            </div>

            {isEditingName ? (
              <form onSubmit={handleUpdateName} style={{ marginTop: 6 }}>
                <input
                  type="text"
                  className="form-input"
                  style={{ padding: "6px 10px", fontSize: "0.9rem", marginBottom: 8 }}
                  value={nameInput}
                  onChange={(e) => setNameInput(e.target.value)}
                  placeholder="Enter full name"
                  autoFocus
                  required
                />
                <div style={{ display: "flex", gap: 8 }}>
                  <button
                    type="submit"
                    className="btn btn-primary btn-sm"
                    disabled={updatingName || !nameInput.trim()}
                    id="btn-save-name"
                  >
                    {updatingName ? "Saving..." : "Save"}
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => setIsEditingName(false)}
                    disabled={updatingName}
                  >
                    Cancel
                  </button>
                </div>
              </form>
            ) : (
              <div style={{ fontWeight: 600, color: "var(--text-pure)", marginTop: 4 }}>
                {profile?.full_name || user?.user_metadata?.full_name || "Not set"}
              </div>
            )}
          </div>

          <div style={{ background: "rgba(11, 19, 43, 0.4)", padding: 14, borderRadius: 10, border: "1px solid var(--border-card)", gridColumn: "span 2" }}>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Organization</span>
            <div style={{ fontWeight: 600, color: "var(--text-pure)", marginTop: 4 }}>
              {profile?.organization || "Independent Compliance Auditor"}
            </div>
          </div>
        </div>
      )}

      {/* Account Control Actions */}
      <div style={{ borderTop: "1px solid var(--border-card)", paddingTop: 24 }}>
        <div style={{ padding: 16, background: "rgba(239, 68, 68, 0.08)", border: "1px solid rgba(239, 68, 68, 0.3)", borderRadius: 10, display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
          <div>
            <div style={{ fontWeight: 700, color: "#FCA5A5" }}>Compliance-Preserved Soft Deletion</div>
            <div style={{ fontSize: "0.8rem", color: "var(--text-mid)" }}>
              Deactivates login credentials. Sanitization certificates remain immutably archived.
            </div>
          </div>

          <button
            className="btn btn-danger btn-sm"
            onClick={handleSoftDelete}
            disabled={deleting}
            type="button"
            id="btn-delete-account"
          >
            {deleting ? "Deactivating..." : "Delete Account"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Authentication Pages (Login, Register, Forgot Password, Reset Password)
// ---------------------------------------------------------------------------
function LoginPage({ setView }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      await api.login(email, password);
      setView("dashboard");
    } catch (err) {
      setError(err.message || "Login failed. Verify credentials.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="glass-panel animate-fade" style={{ maxWidth: 440, margin: "20px auto" }}>
      <div style={{ textAlign: "center", marginBottom: 24 }}>
        <h2 style={{ fontFamily: "var(--font-display)", fontSize: "1.75rem", fontWeight: 800, color: "var(--text-pure)" }}>
          Sign In
        </h2>
        <p style={{ color: "var(--text-mid)", fontSize: "0.9rem", marginTop: 4 }}>
          Access your ZeroTrace compliance console
        </p>
      </div>

      {error && (
        <div style={{ padding: 12, background: "rgba(239, 68, 68, 0.15)", border: "1px solid var(--crimson-danger)", borderRadius: 8, color: "#FCA5A5", fontSize: "0.85rem", marginBottom: 16 }}>
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label className="form-label">Email Address</label>
          <input
            type="email"
            className="form-input"
            placeholder="operator@company.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            id="login-email"
          />
        </div>

        <div className="form-group">
          <div className="form-label">
            <span>Password</span>
            <button
              type="button"
              onClick={() => setView("forgot-password")}
              style={{ background: "transparent", border: "none", color: "var(--cyan-primary)", fontSize: "0.8rem", cursor: "pointer" }}
            >
              Forgot?
            </button>
          </div>
          <input
            type="password"
            className="form-input"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            id="login-password"
          />
        </div>

        <button
          type="submit"
          className="btn btn-primary"
          style={{ width: "100%", marginTop: 10 }}
          disabled={isLoading}
          id="btn-login-submit"
        >
          {isLoading ? "Authenticating..." : "Sign In"}
        </button>
      </form>

      <p style={{ textAlign: "center", fontSize: "0.875rem", color: "var(--text-mid)", marginTop: 20 }}>
        Don't have an account?{" "}
        <button
          type="button"
          onClick={() => setView("register")}
          style={{ background: "transparent", border: "none", color: "var(--cyan-primary)", fontWeight: 600, cursor: "pointer" }}
        >
          Create Account
        </button>
      </p>
    </div>
  );
}

function RegisterPage({ setView }) {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }

    setIsLoading(true);
    try {
      const data = await api.register(email, password, fullName);
      if (data.access_token) {
        setSuccess("Account registered successfully! Redirecting...");
        setTimeout(() => setView("dashboard"), 1200);
      } else {
        setSuccess("Account created successfully! Please sign in.");
        setTimeout(() => setView("login"), 1500);
      }
    } catch (err) {
      setError(err.message || "Registration failed.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="glass-panel animate-fade" style={{ maxWidth: 460, margin: "20px auto" }}>
      <div style={{ textAlign: "center", marginBottom: 24 }}>
        <h2 style={{ fontFamily: "var(--font-display)", fontSize: "1.75rem", fontWeight: 800, color: "var(--text-pure)" }}>
          Create Account
        </h2>
        <p style={{ color: "var(--text-mid)", fontSize: "0.9rem", marginTop: 4 }}>
          Register an authoritative sanitization identity
        </p>
      </div>

      {success && (
        <div style={{ padding: 12, background: "rgba(16, 185, 129, 0.15)", border: "1px solid var(--emerald-success)", borderRadius: 8, color: "#6EE7B7", fontSize: "0.85rem", marginBottom: 16 }}>
          {success}
        </div>
      )}

      {error && (
        <div style={{ padding: 12, background: "rgba(239, 68, 68, 0.15)", border: "1px solid var(--crimson-danger)", borderRadius: 8, color: "#FCA5A5", fontSize: "0.85rem", marginBottom: 16 }}>
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label className="form-label">Full Name</label>
          <input
            type="text"
            className="form-input"
            placeholder="Jane Doe"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            required
            id="register-fullname"
          />
        </div>

        <div className="form-group">
          <label className="form-label">Email Address</label>
          <input
            type="email"
            className="form-input"
            placeholder="jane@organization.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            id="register-email"
          />
        </div>

        <div className="form-group">
          <label className="form-label">Password</label>
          <input
            type="password"
            className="form-input"
            placeholder="At least 6 characters"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            id="register-password"
          />
        </div>

        <div className="form-group">
          <label className="form-label">Confirm Password</label>
          <input
            type="password"
            className="form-input"
            placeholder="Repeat password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            id="register-confirm-password"
          />
        </div>

        <button
          type="submit"
          className="btn btn-primary"
          style={{ width: "100%", marginTop: 8 }}
          disabled={isLoading}
          id="btn-register-submit"
        >
          {isLoading ? "Creating..." : "Register Account"}
        </button>
      </form>

      <p style={{ textAlign: "center", fontSize: "0.875rem", color: "var(--text-mid)", marginTop: 20 }}>
        Already registered?{" "}
        <button
          type="button"
          onClick={() => setView("login")}
          style={{ background: "transparent", border: "none", color: "var(--cyan-primary)", fontWeight: 600, cursor: "pointer" }}
        >
          Sign In
        </button>
      </p>
    </div>
  );
}

function ForgotPasswordPage({ setView }) {
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const sendResetLink = async (e) => {
    e.preventDefault();
    setError("");
    setMessage("");
    setIsLoading(true);

    try {
      await api.forgotPassword(email);
      setMessage("Password recovery email sent. Please check your inbox.");
    } catch (err) {
      setError(err.message || "Failed to send reset link.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="glass-panel animate-fade" style={{ maxWidth: 440, margin: "20px auto" }}>
      <div style={{ textAlign: "center", marginBottom: 24 }}>
        <h2 style={{ fontFamily: "var(--font-display)", fontSize: "1.75rem", fontWeight: 800, color: "var(--text-pure)" }}>
          Reset Password
        </h2>
        <p style={{ color: "var(--text-mid)", fontSize: "0.9rem", marginTop: 4 }}>
          Enter your registered email to receive a secure recovery link
        </p>
      </div>

      {message && (
        <div style={{ padding: 12, background: "rgba(16, 185, 129, 0.15)", border: "1px solid var(--emerald-success)", borderRadius: 8, color: "#6EE7B7", fontSize: "0.85rem", marginBottom: 16 }}>
          {message}
        </div>
      )}

      {error && (
        <div style={{ padding: 12, background: "rgba(239, 68, 68, 0.15)", border: "1px solid var(--crimson-danger)", borderRadius: 8, color: "#FCA5A5", fontSize: "0.85rem", marginBottom: 16 }}>
          {error}
        </div>
      )}

      <form onSubmit={sendResetLink}>
        <div className="form-group">
          <label className="form-label">Email Address</label>
          <input
            type="email"
            className="form-input"
            placeholder="operator@company.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>

        <button
          type="submit"
          className="btn btn-primary"
          style={{ width: "100%", marginTop: 8 }}
          disabled={isLoading}
        >
          {isLoading ? "Sending Link..." : "Send Recovery Link"}
        </button>
      </form>

      <p style={{ textAlign: "center", fontSize: "0.875rem", color: "var(--text-mid)", marginTop: 20 }}>
        Remember your password?{" "}
        <button
          type="button"
          onClick={() => setView("login")}
          style={{ background: "transparent", border: "none", color: "var(--cyan-primary)", fontWeight: 600, cursor: "pointer" }}
        >
          Back to Login
        </button>
      </p>
    </div>
  );
}

function PasswordUpdatePage({ setView }) {
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const handleUpdate = async (e) => {
    e.preventDefault();
    setError("");
    setMessage("");

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setIsLoading(true);
    try {
      await api.resetPassword(password);
      setMessage("Password updated successfully! You can now log in.");
      setTimeout(() => setView("login"), 1500);
    } catch (err) {
      setError(err.message || "Failed to update password.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="glass-panel animate-fade" style={{ maxWidth: 440, margin: "20px auto" }}>
      <div style={{ textAlign: "center", marginBottom: 24 }}>
        <h2 style={{ fontFamily: "var(--font-display)", fontSize: "1.75rem", fontWeight: 800, color: "var(--text-pure)" }}>
          Set New Password
        </h2>
        <p style={{ color: "var(--text-mid)", fontSize: "0.9rem", marginTop: 4 }}>
          Choose a secure replacement password
        </p>
      </div>

      {message && (
        <div style={{ padding: 12, background: "rgba(16, 185, 129, 0.15)", border: "1px solid var(--emerald-success)", borderRadius: 8, color: "#6EE7B7", fontSize: "0.85rem", marginBottom: 16 }}>
          {message}
        </div>
      )}

      {error && (
        <div style={{ padding: 12, background: "rgba(239, 68, 68, 0.15)", border: "1px solid var(--crimson-danger)", borderRadius: 8, color: "#FCA5A5", fontSize: "0.85rem", marginBottom: 16 }}>
          {error}
        </div>
      )}

      <form onSubmit={handleUpdate}>
        <div className="form-group">
          <label className="form-label">New Password</label>
          <input
            type="password"
            className="form-input"
            placeholder="At least 6 characters"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label className="form-label">Confirm New Password</label>
          <input
            type="password"
            className="form-input"
            placeholder="Repeat new password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
          />
        </div>

        <button
          type="submit"
          className="btn btn-primary"
          style={{ width: "100%", marginTop: 8 }}
          disabled={isLoading}
        >
          {isLoading ? "Updating..." : "Save New Password"}
        </button>
      </form>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Root Application
// ---------------------------------------------------------------------------
export default function App() {
  const [view, setView] = useState("home");
  const { user, session, loading } = useAuth();
  const isAuthenticated = Boolean(user);

  const isRecovery = useMemo(() => {
    const hash = window.location.hash || "";
    return hash.includes("type=recovery");
  }, []);

  useEffect(() => {
    if (isRecovery && !isAuthenticated) {
      setView("reset-password");
      return;
    }
    if (isAuthenticated && (view === "home" || view === "login" || view === "register")) {
      setView("dashboard");
    }
    if (!isAuthenticated && (view === "dashboard" || view === "security" || view === "profile")) {
      setView("home");
    }
  }, [isAuthenticated, isRecovery, view]);

  const handleLogout = async () => {
    await api.logout();
    setView("home");
  };

  if (loading) {
    return (
      <main className="zt-app" style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ display: "inline-block", width: 36, height: 36, border: "3px solid rgba(56, 189, 248, 0.2)", borderTopColor: "var(--cyan-primary)", borderRadius: "50%", animation: "spin 1s linear infinite" }} />
          <p style={{ marginTop: 14, color: "var(--text-mid)", fontSize: "0.95rem" }}>
            Connecting to ZeroTrace Authoritative Infrastructure...
          </p>
        </div>
      </main>
    );
  }

  return (
    <div className="zt-app">
      <Navbar view={view} setView={setView} user={user} onLogout={handleLogout} />

      <main className="main-viewport">
        {!isAuthenticated && view === "home" && <HomeScreen setView={setView} />}
        {!isAuthenticated && view === "login" && <LoginPage setView={setView} />}
        {!isAuthenticated && view === "register" && <RegisterPage setView={setView} />}
        {!isAuthenticated && view === "forgot-password" && <ForgotPasswordPage setView={setView} />}
        {!isAuthenticated && view === "reset-password" && <PasswordUpdatePage setView={setView} />}

        {view === "public" && <PublicVerificationPortal setView={setView} />}

        {isAuthenticated && view === "dashboard" && <UserDashboard user={user} session={session} />}
        {isAuthenticated && view === "profile" && <ProfileScreen user={user} session={session} onLogout={handleLogout} />}
      </main>
    </div>
  );
}
