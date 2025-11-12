// web_portal/frontend/src/App.jsx
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { supabase, getCurrentUser } from './Lib/supabase';

// Helper Tailwind classes
const INPUT_CLASS = "block w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 transition duration-150";
const CARD_CLASS = "bg-white p-8 sm:p-10 rounded-xl shadow-2xl w-full max-w-md border border-gray-200 transition duration-300 hover:shadow-xl";

/** Auth Hook - Now using real Supabase */
const useAuth = () => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Get initial session
        supabase.auth.getSession().then(({ data: { session } }) => {
            setUser(session?.user ?? null);
            setLoading(false);
        });

        // Listen for auth changes
        const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
            setUser(session?.user ?? null);
        });

        return () => subscription.unsubscribe();
    }, []);

    return { user, loading };
};

/** Mode Tab Component */
const ModeTab = ({ mode, currentMode, setMode, label }) => {
    const isActive = mode === currentMode;
    return (
        <button
            className={`flex-1 py-2 px-3 text-sm font-semibold rounded-lg transition duration-150 ${
                isActive 
                ? 'bg-white text-indigo-700 shadow-md' 
                : 'text-gray-600 hover:bg-gray-200'
            }`}
            onClick={() => setMode(mode)}
        >
            {label}
        </button>
    );
};

/** PUBLIC VERIFICATION PORTAL */
const PublicVerificationPortal = ({ setView }) => {
    const [certId, setCertId] = useState('');
    const [verificationResult, setVerificationResult] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [verificationMode, setVerificationMode] = useState('manual');
    const [cameraStatus, setCameraStatus] = useState('idle');
    const [uploadedFile, setUploadedFile] = useState(null);
    
    const videoRef = useRef(null);
    const [videoStream, setVideoStream] = useState(null);

    const stopCamera = useCallback(() => {
        if (videoStream) {
            videoStream.getTracks().forEach(track => track.stop());
            setVideoStream(null);
            setCameraStatus('idle');
        }
    }, [videoStream]);

    useEffect(() => {
        return () => stopCamera();
    }, [stopCamera]);

    const handleCameraRequest = async () => {
        if (cameraStatus === 'active') {
            stopCamera();
            return;
        }

        setCameraStatus('requested');
        setVerificationResult(null);

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ 
                video: { facingMode: "environment" } 
            });
            
            if (videoRef.current) {
                videoRef.current.srcObject = stream;
            }
            
            setVideoStream(stream);
            setCameraStatus('active');
        } catch (error) {
            setCameraStatus('error');
            setVideoStream(null);
            console.error("Camera access denied:", error);
        }
    };

    // Real verification via API
    const handleVerify = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        setVerificationResult(null);

        try {
            const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:5000';
            const response = await fetch(`${apiUrl}/api/verify/id/${certId}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            const data = await response.json();
            setVerificationResult(data);
        } catch (error) {
            console.error('Verification error:', error);
            setVerificationResult({
                status: 'Error',
                message: 'Failed to verify certificate. Please try again.'
            });
        } finally {
            setIsLoading(false);
        }
    };

    const handleFileUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        setUploadedFile(file);
        setIsLoading(true);
        setVerificationResult(null);

        try {
            const formData = new FormData();
            formData.append('file', file);

            const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:5000';
            const response = await fetch(`${apiUrl}/api/verify/file`, {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            setVerificationResult(data);
        } catch (error) {
            console.error('Upload verification error:', error);
            setVerificationResult({
                status: 'Error',
                message: 'Failed to verify certificate file. Please try again.'
            });
        } finally {
            setIsLoading(false);
        }
    };

    const renderResult = () => {
        if (!verificationResult) return null;

        const { status, message, details } = verificationResult;

        const statusClasses = {
            Verified: 'bg-green-100 text-green-800 border-green-400',
            Expired: 'bg-yellow-100 text-yellow-800 border-yellow-400',
            NotFound: 'bg-red-100 text-red-800 border-red-400',
            Revoked: 'bg-red-100 text-red-800 border-red-400',
            Error: 'bg-gray-100 text-gray-800 border-gray-400',
        };

        return (
            <div className={`mt-8 p-6 rounded-lg border-l-4 shadow-md ${statusClasses[status] || 'bg-gray-100 text-gray-800 border-gray-400'}`}>
                <h3 className="text-xl font-bold mb-3">{message}</h3>
                {details && (
                    <div className="space-y-2 text-sm">
                        {details.device_name && <p><strong>Device:</strong> {details.device_name}</p>}
                        {details.device_model && <p><strong>Model:</strong> {details.device_model}</p>}
                        {details.wipe_method && <p><strong>Wipe Method:</strong> {details.wipe_method}</p>}
                        {details.wipe_date && <p><strong>Wipe Date:</strong> {new Date(details.wipe_date).toLocaleDateString()}</p>}
                        {details.status && <p><strong>Status:</strong> {details.status}</p>}
                    </div>
                )}
            </div>
        );
    };

    const renderModeContent = () => {
        switch (verificationMode) {
            case 'pdf':
                return (
                    <div className="space-y-6">
                        <div className="border-2 border-dashed border-indigo-300 p-8 rounded-xl text-center bg-indigo-50 hover:bg-indigo-100 transition duration-150 cursor-pointer">
                            <input 
                                type="file" 
                                accept=".pdf,.json" 
                                className="hidden" 
                                id="pdf-upload"
                                onChange={handleFileUpload}
                            />
                            <label htmlFor="pdf-upload" className="block cursor-pointer">
                                <svg xmlns="http://www.w3.org/2000/svg" className="mx-auto h-10 w-10 text-indigo-500 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 014 4v2a4 4 0 00-3.5-3.966M16 12h2a2 2 0 012 2v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5a2 2 0 012-2h2m4-7v12m0 0l-4-4m4 4l4-4" />
                                </svg>
                                <p className="text-gray-700 font-semibold">Click or drag a certificate file here</p>
                                <p className="text-sm text-gray-500 mt-1">Accepts PDF or JSON certificates</p>
                                {uploadedFile && <p className="text-sm text-indigo-600 mt-2">Selected: {uploadedFile.name}</p>}
                            </label>
                        </div>
                    </div>
                );
            case 'camera':
                return (
                    <div className="space-y-6 text-center">
                        <div className="p-1 border-4 border-dashed border-gray-300 rounded-xl bg-black h-96 flex flex-col items-center justify-center relative overflow-hidden">
                            {cameraStatus === 'active' ? (
                                <>
                                    <video 
                                        ref={videoRef} 
                                        autoPlay 
                                        playsInline 
                                        className="w-full h-full object-cover rounded-lg"
                                        onLoadedMetadata={() => videoRef.current.play()}
                                    />
                                    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                                        <div className="w-3/4 h-3/4 border-4 border-green-500 rounded-lg animate-pulse" style={{boxShadow: '0 0 0 9999px rgba(0,0,0,0.5)'}}></div>
                                        <p className="absolute text-white bottom-4 font-semibold text-lg bg-black bg-opacity-50 px-3 py-1 rounded">Scanning Live Feed...</p>
                                    </div>
                                </>
                            ) : cameraStatus === 'idle' ? (
                                <p className="text-gray-400 font-medium">Click the button below to start the camera and scan a QR code.</p>
                            ) : cameraStatus === 'requested' ? (
                                <p className="text-indigo-400 animate-pulse font-medium">Awaiting camera permission...</p>
                            ) : (
                                <p className="text-red-500 font-medium p-4">
                                    Access Denied. Please ensure your browser permissions allow camera use and try again.
                                </p>
                            )}
                        </div>
                        
                        <button 
                            type="button" 
                            className={`w-full font-semibold py-3 rounded-lg transition duration-150 shadow-lg flex items-center justify-center ${
                                cameraStatus === 'active' 
                                ? 'bg-red-600 hover:bg-red-700 text-white' 
                                : 'bg-indigo-600 hover:bg-indigo-700 text-white'
                            }`}
                            onClick={handleCameraRequest}
                            disabled={cameraStatus === 'requested'}
                        >
                            {cameraStatus === 'active' ? 'Stop Camera Scan' : 'Start Camera Scan'}
                        </button>
                    </div>
                );
            case 'manual':
            default:
                return (
                    <form onSubmit={handleVerify} className="space-y-6">
                        <div>
                            <label htmlFor="cert-id" className="block text-sm font-medium text-gray-700 mb-1">Certificate ID</label>
                            <input
                                type="text"
                                id="cert-id"
                                className={INPUT_CLASS}
                                placeholder="e.g., CERT-A1B2C3D4E5F6G7H8"
                                value={certId}
                                onChange={(e) => setCertId(e.target.value)}
                                required
                            />
                        </div>
                        
                        <button 
                            type="submit" 
                            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3 rounded-lg transition duration-150 shadow-lg flex items-center justify-center"
                            disabled={isLoading}
                        >
                            {isLoading ? (
                                <div className="flex items-center">
                                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                    </svg>
                                    Verifying...
                                </div>
                            ) : (
                                'Verify Certificate'
                            )}
                        </button>
                    </form>
                );
        }
    };
    
    return (
        <div className="flex items-center justify-center w-full flex-grow py-12">
            <div className={CARD_CLASS.replace('max-w-md', 'max-w-2xl')}> 
                <h2 className="text-3xl font-extrabold text-center text-indigo-700 mb-2">
                    Public Certificate Verification
                </h2>
                <p className="text-center text-gray-500 mb-8">
                    Choose a method to verify the authenticity of your document.
                </p>

                <div className="flex justify-center mb-8 bg-gray-100 p-1 rounded-xl shadow-inner">
                    <ModeTab 
                        mode="manual" 
                        currentMode={verificationMode} 
                        setMode={setVerificationMode}
                        label="Manual ID Entry"
                    />
                    <ModeTab 
                        mode="pdf" 
                        currentMode={verificationMode} 
                        setMode={setVerificationMode}
                        label="File Upload"
                    />
                    <ModeTab 
                        mode="camera" 
                        currentMode={verificationMode} 
                        setMode={setVerificationMode}
                        label="Camera Scan"
                    />
                </div>

                {renderModeContent()}
                {renderResult()}
                
                <div className="text-center mt-8 pt-6 border-t border-gray-100">
                    <button 
                        className="text-sm font-medium text-blue-600 hover:text-blue-800 transition duration-150"
                        onClick={() => setView('login')}
                    >
                        &larr; Back to Login / Management
                    </button>
                </div>
            </div>
        </div>
    );
};

/** LOGIN PAGE */
const LoginPage = ({ setView, setIsAuthenticated }) => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        setError('');

        try {
            const { data, error } = await supabase.auth.signInWithPassword({
                email,
                password,
            });

            if (error) throw error;

            if (data.user) {
                setIsAuthenticated(true);
                setView('dashboard');
            }
        } catch (error) {
            setError(error.message);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex items-center justify-center w-full flex-grow py-12">
            <div className={CARD_CLASS}>
                <h2 className="text-3xl font-extrabold text-center text-blue-700 mb-2">
                    Verification Portal Login
                </h2>
                <p className="text-center text-gray-500 mb-8">Sign in to manage your certificates.</p>

                {error && (
                    <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-lg">
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-6">
                    <div>
                        <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">Email address</label>
                        <input 
                            type="email" 
                            id="email" 
                            className={INPUT_CLASS} 
                            placeholder="user@example.com" 
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required 
                        />
                    </div>
                    
                    <div>
                        <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                        <input 
                            type="password" 
                            id="password" 
                            className={INPUT_CLASS} 
                            placeholder="••••••••" 
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required 
                        />
                    </div>
                    
                    <div className="flex justify-end mb-4">
                        <button 
                            type="button" 
                            className="text-sm font-medium text-indigo-600 hover:text-indigo-500 transition duration-150"
                            onClick={() => setView('forgot-password')}
                        >
                            Forgot Password?
                        </button>
                    </div>

                    <button 
                        type="submit" 
                        className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 rounded-lg transition duration-150 shadow-lg disabled:bg-gray-400"
                        disabled={isLoading}
                    >
                        {isLoading ? 'Logging in...' : 'Log In'}
                    </button>
                </form>

                <div className="mt-8 pt-6 border-t border-gray-100 space-y-4">
                    <div className="text-center text-sm">
                        <p className="text-gray-600">Don't have an account?</p>
                        <button 
                            className="font-medium text-green-600 hover:text-green-700 transition duration-150"
                            onClick={() => setView('register')}
                        >
                            Create Account
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

/** REGISTER PAGE */
const RegisterPage = ({ setView }) => {
    const [formData, setFormData] = useState({
        email: '',
        password: '',
        confirmPassword: '',
        fullName: ''
    });
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        
        if (formData.password !== formData.confirmPassword) {
            setError("Passwords don't match");
            return;
        }

        setIsLoading(true);
        setError('');

        try {
            const { data, error } = await supabase.auth.signUp({
                email: formData.email,
                password: formData.password,
                options: {
                    data: {
                        full_name: formData.fullName,
                    }
                }
            });

            if (error) throw error;

            // Create user profile
            if (data.user) {
                const { error: profileError } = await supabase
                    .from('user_profiles')
                    .insert([
                        { 
                            id: data.user.id, 
                            full_name: formData.fullName 
                        }
                    ]);

                if (profileError) console.error('Profile creation error:', profileError);
            }

            alert('Registration successful! Please check your email to verify your account.');
            setView('login');
        } catch (error) {
            setError(error.message);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex items-center justify-center w-full flex-grow py-12">
            <div className={CARD_CLASS}>
                <h2 className="text-3xl font-extrabold text-center text-green-700 mb-2">
                    Create Account
                </h2>
                <p className="text-center text-gray-500 mb-8">Join the certification management platform.</p>

                {error && (
                    <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-lg">
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-6">
                    <div>
                        <label htmlFor="fullName" className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
                        <input 
                            type="text" 
                            id="fullName" 
                            className={INPUT_CLASS} 
                            placeholder="Your Name" 
                            value={formData.fullName}
                            onChange={(e) => setFormData({...formData, fullName: e.target.value})}
                            required 
                        />
                    </div>
                    
                    <div>
                        <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                        <input 
                            type="email" 
                            id="email" 
                            className={INPUT_CLASS} 
                            placeholder="user@example.com" 
                            value={formData.email}
                            onChange={(e) => setFormData({...formData, email: e.target.value})}
                            required 
                        />
                    </div>
                    
                    <div>
                        <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                        <input 
                            type="password" 
                            id="password" 
                            className={INPUT_CLASS} 
                            placeholder="••••••••" 
                            value={formData.password}
                            onChange={(e) => setFormData({...formData, password: e.target.value})}
                            required 
                        />
                    </div>

                    <div>
                        <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-1">Confirm Password</label>
                        <input 
                            type="password" 
                            id="confirmPassword" 
                            className={INPUT_CLASS} 
                            placeholder="••••••••" 
                            value={formData.confirmPassword}
                            onChange={(e) => setFormData({...formData, confirmPassword: e.target.value})}
                            required 
                        />
                    </div>
                    
                    <button 
                        type="submit" 
                        className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-3 rounded-lg transition duration-150 shadow-lg mt-6 disabled:bg-gray-400"
                        disabled={isLoading}
                    >
                        {isLoading ? 'Creating Account...' : 'Register'}
                    </button>
                </form>
                <div className="text-center mt-6 pt-4 border-t border-gray-100">
                    <button 
                        className="text-sm font-medium text-blue-600 hover:text-blue-800 transition duration-150"
                        onClick={() => setView('login')}
                    >
                        &larr; Already have an account? Sign In
                    </button>
                </div>
            </div>
        </div>
    );
};

/** FORGOT PASSWORD */
const ForgotPassword = ({ setView }) => {
    const [email, setEmail] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [message, setMessage] = useState('');
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        setError('');
        setMessage('');

        try {
            const { error } = await supabase.auth.resetPasswordForEmail(email, {
                redirectTo: `${window.location.origin}/reset-password`,
            });

            if (error) throw error;

            setMessage('Password reset link sent! Check your email.');
        } catch (error) {
            setError(error.message);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex items-center justify-center w-full flex-grow py-12">
            <div className={CARD_CLASS}>
                <h2 className="text-3xl font-extrabold text-center text-purple-700 mb-2">
                    Password Reset
                </h2>
                <p className="text-center text-gray-500 mb-8">Enter your email to receive a password reset link.</p>
                
                {message && (
                    <div className="mb-4 p-3 bg-green-100 border border-green-400 text-green-700 rounded-lg">
                        {message}
                    </div>
                )}

                {error && (
                    <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-lg">
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-6">
                    <div>
                        <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">Email address</label>
                        <input 
                            type="email" 
                            id="email" 
                            className={INPUT_CLASS} 
                            placeholder="user@example.com" 
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required 
                        />
                    </div>
                    
                    <button 
                        type="submit" 
                        className="w-full bg-purple-600 hover:bg-purple-700 text-white font-semibold py-3 rounded-lg transition duration-150 shadow-lg mt-6 disabled:bg-gray-400"
                        disabled={isLoading}
                    >
                        {isLoading ? 'Sending...' : 'Send Reset Link'}
                    </button>
                </form>
                <div className="text-center mt-6 pt-4 border-t border-gray-100">
                    <button 
                        className="text-sm font-medium text-blue-600 hover:text-blue-800 transition duration-150"
                        onClick={() => setView('login')}
                    >
                        &larr; Back to Login
                    </button>
                </div>
            </div>
        </div>
    );
};

/** USER DASHBOARD */
const UserDashboard = () => {
    const { user } = useAuth();
    const [certificates, setCertificates] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (user) {
            fetchCertificates();
        }
    }, [user]);

    const fetchCertificates = async () => {
        try {
            const { data, error } = await supabase
                .from('certificates')
                .select('*')
                .eq('user_id', user.id)
                .order('created_at', { ascending: false });

            if (error) throw error;

            setCertificates(data || []);
        } catch (error) {
            console.error('Error fetching certificates:', error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center w-full h-64">
                <div className="text-gray-500">Loading certificates...</div>
            </div>
        );
    }

    return (
        <div className="p-4 sm:p-8 w-full max-w-4xl mx-auto"> 
            <h1 className="text-3xl font-bold mb-4 text-center text-gray-800">My Certificate Dashboard</h1>
            
            <div className="text-center mb-6 p-3 bg-gray-100 rounded-lg max-w-lg mx-auto">
                <p className="text-sm font-medium text-gray-500">
                    User: <span className="font-mono text-gray-700">{user?.email}</span>
                </p>
            </div>

            <div className="bg-white p-6 sm:p-8 rounded-xl shadow-xl border border-gray-200">
                <div className="flex flex-col sm:flex-row justify-between items-center mb-6 pb-4 border-b border-gray-100">
                    <h2 className="text-2xl font-semibold text-gray-700 mb-3 sm:mb-0">My Certificates</h2>
                </div>

                {certificates.length === 0 ? (
                    <div className="text-center py-8 text-gray-500">
                        No certificates found. Your wiped devices will appear here.
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {certificates.map(cert => (
                                    <tr key={cert.id} className="hover:bg-blue-50 transition duration-150">
                                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                            {cert.device_name || 'Unknown Device'}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                            {cert.wipe_method}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                            {new Date(cert.created_at).toLocaleDateString()}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                                                cert.status === 'verified' ? 'bg-green-100 text-green-800' :
                                                cert.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                                                cert.status === 'revoked' ? 'bg-red-100 text-red-800' :
                                                'bg-gray-100 text-gray-800'
                                            }`}>
                                                {cert.status}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                                            <div className="flex justify-center space-x-2">
                                                <a
                                                    href={cert.pdf_url}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="text-xs px-3 py-1 bg-indigo-500 text-white rounded-md hover:bg-indigo-600 transition duration-150"
                                                >
                                                    View PDF
                                                </a>
                                                <a
                                                    href={cert.json_url}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="text-xs px-3 py-1 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition duration-150"
                                                >
                                                    JSON
                                                </a>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
};

/** MAIN APP */
const App = () => {
    const [view, setView] = useState('login'); 
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const { user, loading } = useAuth();

    useEffect(() => {
        if (user) {
            setIsAuthenticated(true);
            if (view === 'login' || view === 'register') {
                setView('dashboard');
            }
        } else {
            setIsAuthenticated(false);
            if (view === 'dashboard') {
                setView('login');
            }
        }
    }, [user]);

    const handleLogout = async () => {
        await supabase.auth.signOut();
        setIsAuthenticated(false);
        setView('login');
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen bg-gray-50">
                <div className="text-gray-500">Loading...</div>
            </div>
        );
    }

    const renderContent = () => {
        if (!isAuthenticated) {
            switch (view) {
                case 'register':
                    return <RegisterPage setView={setView} />;
                case 'forgot-password':
                    return <ForgotPassword setView={setView} />;
                case 'public':
                    return <PublicVerificationPortal setView={setView} />;
                case 'login':
                default:
                    return <LoginPage setView={setView} setIsAuthenticated={setIsAuthenticated} />;
            }
        }
        
        switch (view) {
            case 'public':
                return <PublicVerificationPortal setView={setView} />;
            case 'dashboard':
            default:
                return <UserDashboard />;
        }
    };

    return (
        <div className="flex flex-col items-center justify-center bg-gray-50 min-h-screen w-full p-4 sm:p-8 font-sans">
            <div className="w-full max-w-6xl">
                <div className="w-full"> 
                    <header className="flex justify-end p-4 sm:p-6 pb-2">
                        <div className='flex space-x-4 items-center'>
                            {!isAuthenticated ? (
                                <>
                                    {view !== 'public' && view !== 'login' && view !== 'register' && view !== 'forgot-password' && (
                                        <button
                                            onClick={() => setView('public')}
                                            className="px-4 py-2 text-indigo-600 font-semibold rounded-lg hover:bg-indigo-50 transition duration-150 border border-indigo-600"
                                        >
                                            Public Verification
                                        </button>
                                    )}
                                    
                                    {(view !== 'login' && view !== 'register' && view !== 'forgot-password') && (
                                        <button
                                            onClick={() => setView('login')}
                                            className="px-4 py-2 text-blue-600 font-semibold rounded-lg hover:bg-blue-50 transition duration-150 border border-blue-600"
                                        >
                                            Log In
                                        </button>
                                    )}
                                </>
                            ) : (
                                <>
                                    {view !== 'dashboard' && (
                                        <button 
                                            onClick={() => setView('dashboard')}
                                            className="px-4 py-2 text-gray-600 font-semibold rounded-lg hover:bg-gray-100 transition duration-150"
                                        >
                                            Dashboard
                                        </button>
                                    )}
                                    
                                    {view !== 'public' && (
                                        <button 
                                            onClick={() => setView('public')}
                                            className="px-4 py-2 text-indigo-600 font-semibold rounded-lg hover:bg-indigo-50 transition duration-150 border border-indigo-600"
                                        >
                                            Public Verification
                                        </button>
                                    )}
                                    
                                    <button 
                                        onClick={handleLogout}
                                        className='px-6 py-2 bg-red-500 text-white font-semibold rounded-lg shadow-md hover:bg-red-600 transition duration-150'
                                    >
                                        Logout
                                    </button>
                                </>
                            )}
                        </div>
                    </header>
                    
                    <main className="flex-grow flex flex-col justify-center items-center">
                        {renderContent()}
                    </main>
                </div>
            </div>
        </div>
    );
};

export default App;