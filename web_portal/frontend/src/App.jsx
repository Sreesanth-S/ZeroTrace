import React, { useEffect, useMemo, useState } from "react";
import { supabase, supabaseKey } from "./lib/supabase";
import QrScanner from "./components/QrScanner";

const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:5000";

function useAuth() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
      setLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });

    return () => subscription.unsubscribe();
  }, []);

  return { user, loading };
}

function ActionButton({ children, className = "", ...props }) {
  return (
    <button className={`pill-button ${className}`} {...props}>
      {children}
    </button>
  );
}

function PrimaryCard({ children, className = "" }) {
  return <section className={`zt-card ${className}`}>{children}</section>;
}

function Field({ label, type = "text", value, onChange, placeholder, required = true }) {
  return (
    <label className="field-group">
      <span>{label}</span>
      <input
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        required={required}
      />
    </label>
  );
}

function PublicVerificationPortal({ setView, showBack = true }) {
  const [mode, setMode] = useState("upload");
  const [uploadedFileName, setUploadedFileName] = useState("");
  const [verificationResult, setVerificationResult] = useState(null);

  const verifyByHash = async (hash) => {
    if (!hash) return;
    setVerificationResult(null);
    try {
      const response = await fetch(`${apiUrl}/api/verify/hash`, {
        method: "POST",
        headers: { "Content-Type": "application/json", apikey: supabaseKey },
        body: JSON.stringify({ hash }),
      });
      const data = await response.json();
      if (!response.ok) {
        setVerificationResult({
          status: "Error",
          message: data?.error || data?.message || `Verification failed (${response.status})`,
        });
        return;
      }
      setVerificationResult(data);
    } catch {
      setVerificationResult({ status: "Error", message: "Verification request failed." });
    }
  };

  const verifyByFile = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploadedFileName(file.name);
    setVerificationResult(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch(`${apiUrl}/api/verify/file`, {
        method: "POST",
        headers: { apikey: supabaseKey },
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) {
        setVerificationResult({
          status: "Error",
          message: data?.error || data?.message || `File verification failed (${response.status})`,
        });
        return;
      }
      setVerificationResult(data);
    } catch {
      setVerificationResult({ status: "Error", message: "File verification failed." });
    }
  };

  const extractVerificationHash = (rawScanValue) => {
    const value = String(rawScanValue || "").trim();
    if (!value) return "";

    try {
      const parsed = JSON.parse(value);
      if (parsed?.verification_hash) return String(parsed.verification_hash).trim();
    } catch {
      // Continue with URL/plain-text parsing
    }

    try {
      const asUrl = new URL(value);
      const queryHash = asUrl.searchParams.get("hash");
      if (queryHash) return queryHash.trim();
    } catch {
      // Not a URL, continue
    }

    const hexHashRegex = /^[A-Fa-f0-9]{64}$/;
    if (hexHashRegex.test(value)) {
      return value;
    }

    return "";
  };

  const handleQrResult = async (decodedText) => {
    const hash = extractVerificationHash(decodedText);
    if (!hash) {
      setVerificationResult({
        status: "Invalid",
        message: "QR code does not contain a valid verification hash.",
      });
      return;
    }
    await verifyByHash(hash);
  };

  return (
    <PrimaryCard className="wide-card">
      <h2 className="screen-title contrast">Public Verification Portal</h2>

      <div className="portal-controls">
        <ActionButton onClick={() => setMode("upload")}>Upload Document</ActionButton>
        <ActionButton onClick={() => setMode("scan")}>QR Scan</ActionButton>
      </div>

      {mode === "upload" ? (
        <div className="upload-area">
          <input type="file" id="portal-file" accept=".pdf,.json" onChange={verifyByFile} />
          <label htmlFor="portal-file">{uploadedFileName || "Upload your PDF or JSON certificate"}</label>
        </div>
      ) : (
        <div className="scan-area">
          <div className="camera-box">
            <QrScanner onResult={handleQrResult} />
          </div>
        </div>
      )}

      {verificationResult && (
        <div className={`result-box ${verificationResult.status?.toLowerCase() || "info"}`}>
          <strong>{verificationResult.status || "Result"}:</strong>{" "}
          {verificationResult.message || verificationResult.error || "Unknown response"}
        </div>
      )}

      {showBack && (
        <button className="text-link" type="button" onClick={() => setView("home")}>
          Back
        </button>
      )}
    </PrimaryCard>
  );
}

function HomeScreen({ setView }) {
  return (
    <PrimaryCard className="landing-card">
      <h1 className="brand-title">
        <span>Zero</span>Trace
      </h1>
      <ActionButton onClick={() => setView("login")}>Login</ActionButton>
      <p className="support-line">
        Don't have account?{" "}
        <button className="text-link inline" type="button" onClick={() => setView("register")}>
          Create new account
        </button>
      </p>
      <ActionButton onClick={() => setView("public")}>Public Verification Portal</ActionButton>
    </PrimaryCard>
  );
}

function LoginPage({ setView }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setIsLoading(true);
    try {
      const { error: authError } = await supabase.auth.signInWithPassword({ email, password });
      if (authError) throw authError;
    } catch (err) {
      setError(err.message || "Login failed.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <PrimaryCard className="form-card">
      <h2 className="screen-title">Login</h2>
      {error && <p className="error-line">{error}</p>}
      <form className="form-stack" onSubmit={handleSubmit}>
        <Field label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <Field label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        <ActionButton type="submit" disabled={isLoading}>
          {isLoading ? "Logging in..." : "Login"}
        </ActionButton>
      </form>
      <button className="text-link" type="button" onClick={() => setView("forgot-password")}>
        Forgot password?
      </button>
    </PrimaryCard>
  );
}

function RegisterPage({ setView }) {
  const [formData, setFormData] = useState({
    fullName: "",
    email: "",
    password: "",
    confirmPassword: "",
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setSuccess("");
    if (formData.password !== formData.confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (formData.password.length < 6) {
      setError("Password must be at least 6 characters long.");
      return;
    }
    setIsLoading(true);
    try {
      const { data, error: signUpError } = await supabase.auth.signUp({
        email: formData.email,
        password: formData.password,
        options: { data: { full_name: formData.fullName } },
      });
      if (signUpError) throw signUpError;

      if (data.session) {
        setSuccess("Account created successfully!");
      } else if (data.user) {
        setSuccess("Account created! Please check your email for the verification link, then log in.");
      }
    } catch (err) {
      setError(err.message || "Registration failed.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <PrimaryCard className="form-card">
      <h2 className="screen-title">Create Account</h2>
      {success && <p className="success-line">{success}</p>}
      {error && <p className="error-line">{error}</p>}
      <form className="form-stack" onSubmit={handleSubmit}>
        <Field
          label="Full Name"
          value={formData.fullName}
          onChange={(event) => setFormData((prev) => ({ ...prev, fullName: event.target.value }))}
        />
        <Field
          label="Email"
          type="email"
          value={formData.email}
          onChange={(event) => setFormData((prev) => ({ ...prev, email: event.target.value }))}
        />
        <Field
          label="Password"
          type="password"
          value={formData.password}
          onChange={(event) => setFormData((prev) => ({ ...prev, password: event.target.value }))}
        />
        <Field
          label="Confirm password"
          type="password"
          value={formData.confirmPassword}
          onChange={(event) =>
            setFormData((prev) => ({ ...prev, confirmPassword: event.target.value }))
          }
        />
        <ActionButton type="submit" className="small-pill" disabled={isLoading}>
          {isLoading ? "Creating..." : "Done"}
        </ActionButton>
      </form>
      <button className="text-link" type="button" onClick={() => setView("login")}>
        Back to Login
      </button>
    </PrimaryCard>
  );
}

function ForgotPasswordPage({ setView }) {
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const sendResetLink = async (event) => {
    event.preventDefault();
    setError("");
    setMessage("");
    setIsLoading(true);
    try {
      const { error: resetError } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/reset-password`,
      });
      if (resetError) throw resetError;
      setMessage("Reset link sent.");
    } catch (err) {
      setError(err.message || "Could not send reset link.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <PrimaryCard className="form-card">
      <h2 className="screen-title">Password Reset</h2>
      {message && <p className="success-line">{message}</p>}
      {error && <p className="error-line">{error}</p>}
      <form className="form-stack" onSubmit={sendResetLink}>
        <Field label="Email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
        <button className="text-link inline right" type="button" onClick={sendResetLink}>
          Resend link
        </button>
        <ActionButton type="submit" disabled={isLoading}>
          {isLoading ? "Sending..." : "Send Reset Link"}
        </ActionButton>
      </form>
      <button className="text-link" type="button" onClick={() => setView("login")}>
        Back
      </button>
    </PrimaryCard>
  );
}

function PasswordUpdatePage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const handleUpdate = async (event) => {
    event.preventDefault();
    setError("");
    setMessage("");
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    setIsLoading(true);
    try {
      const { error: updateError } = await supabase.auth.updateUser({ password });
      if (updateError) throw updateError;
      setMessage("Password updated.");
    } catch (err) {
      setError(err.message || "Could not update password.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <PrimaryCard className="form-card">
      <h2 className="screen-title">Password Reset</h2>
      {message && <p className="success-line">{message}</p>}
      {error && <p className="error-line">{error}</p>}
      <form className="form-stack" onSubmit={handleUpdate}>
        <Field label="Email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
        <Field
          label="Password"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
        <Field
          label="Confirm password"
          type="password"
          value={confirmPassword}
          onChange={(event) => setConfirmPassword(event.target.value)}
        />
        <ActionButton type="submit" className="small-pill" disabled={isLoading}>
          {isLoading ? "Updating..." : "Done"}
        </ActionButton>
      </form>
    </PrimaryCard>
  );
}

function UserDashboard({ user }) {
  const [certificates, setCertificates] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchCertificates = async () => {
      try {
        const { data, error } = await supabase
          .from("certificates")
          .select("*")
          .eq("user_id", user.id)
          .order("created_at", { ascending: false });
        if (error) throw error;
        setCertificates(data || []);
      } catch {
        setCertificates([]);
      } finally {
        setLoading(false);
      }
    };
    fetchCertificates();
  }, [user]);

  return (
    <section className="dashboard-shell">
      <h1 className="dashboard-title">Dashboard</h1>
      <div className="user-banner">User: {user.email}</div>

      <PrimaryCard className="dashboard-card">
        <h2 className="dashboard-subtitle">My Certificates</h2>
        {loading ? (
          <p className="empty-line">Loading...</p>
        ) : certificates.length === 0 ? (
          <p className="empty-line">No found</p>
        ) : (
          <div className="certificate-list">
            {certificates.map((cert) => (
              <article className="certificate-item" key={cert.id}>
                <div>
                  <strong>{cert.device_name || "Unknown device"}</strong>
                  <p>{cert.wipe_method || "Unknown method"}</p>
                </div>
                <div className="certificate-actions">
                  {cert.pdf_url && (
                    <a href={cert.pdf_url} target="_blank" rel="noreferrer">
                      PDF
                    </a>
                  )}
                  {cert.json_url && (
                    <a href={cert.json_url} target="_blank" rel="noreferrer">
                      JSON
                    </a>
                  )}
                </div>
              </article>
            ))}
          </div>
        )}
      </PrimaryCard>
    </section>
  );
}

export default function App() {
  const [view, setView] = useState("home");
  const { user, loading } = useAuth();
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
    if (!isAuthenticated && view === "dashboard") {
      setView("home");
    }
  }, [isAuthenticated, isRecovery, view]);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    setView("home");
  };

  if (loading) {
    return <main className="zt-app"><p className="empty-line">Loading...</p></main>;
  }

  return (
    <main className={`zt-app ${isAuthenticated ? "dashboard-bg" : ""}`}>
      <header className="top-nav">
        {isAuthenticated ? (
          <>
            <button className="pill-button nav-pill" onClick={() => setView("public")} type="button">
              Public verification
            </button>
            <button className="logout-button" onClick={handleLogout} type="button">
              Logout
            </button>
          </>
        ) : (
          view !== "home" && (
            <button className="pill-button nav-pill" onClick={() => setView("home")} type="button">
              Home
            </button>
          )
        )}
      </header>

      {!isAuthenticated && view === "home" && <HomeScreen setView={setView} />}
      {!isAuthenticated && view === "login" && <LoginPage setView={setView} />}
      {!isAuthenticated && view === "register" && <RegisterPage setView={setView} />}
      {!isAuthenticated && view === "forgot-password" && <ForgotPasswordPage setView={setView} />}
      {!isAuthenticated && view === "reset-password" && <PasswordUpdatePage />}

      {view === "public" && <PublicVerificationPortal setView={setView} showBack={!isAuthenticated} />}
      {isAuthenticated && view === "dashboard" && <UserDashboard user={user} />}
    </main>
  );
}
