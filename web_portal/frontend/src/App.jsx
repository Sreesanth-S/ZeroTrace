import React, { useState, useEffect, useRef, useCallback } from 'react';
// Note: In a real-world scenario, you would be importing Firebase functions here.

// Helper Tailwind class for input fields
const INPUT_CLASS = "block w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 transition duration-150";
const CARD_CLASS = "bg-white p-8 sm:p-10 rounded-xl shadow-2xl w-full max-w-md border border-gray-200 transition duration-300 hover:shadow-xl";

/** * PLACEHOLDER HOOK (Handles mock user ID/Auth status)
 * This must be included as all components rely on a user ID context.
 */
const useAuthAndDb = () => {
    // NOTE: In a real application, this is where Firebase would be initialized
    // using __firebase_config and __initial_auth_token.
    const [userId, setUserId] = useState(null);
    const [isAuthReady, setIsAuthReady] = useState(true); // Mock readiness

    useEffect(() => {
        // Mocking authentication check
        const mockSignIn = () => {
            // Simulate successful sign-in
            setUserId(crypto.randomUUID());
        };

        if (typeof __initial_auth_token !== 'undefined') {
            // Actual Firebase sign-in with custom token logic goes here
            mockSignIn();
        } else {
            // Actual Firebase anonymous sign-in logic goes here
            mockSignIn();
        }
    }, []);

    return { userId, isAuthReady };
};


/** * HELPER COMPONENT: Tab for Mode Selection
 */
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


/** * PUBLIC VERIFICATION PORTAL 
 */
const PublicVerificationPortal = ({ setView }) => {
    const [certId, setCertId] = useState('');
    const [verificationResult, setVerificationResult] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [verificationMode, setVerificationMode] = useState('manual');
    const [cameraStatus, setCameraStatus] = useState('idle'); // 'idle', 'requested', 'active', 'error'
    
    // Hooks for Camera Access
    const videoRef = useRef(null); // Ref to hold the HTML <video> element
    const [videoStream, setVideoStream] = useState(null); // State to hold the MediaStream object

    // Function to stop the camera stream and clean up
    const stopCamera = useCallback(() => {
        if (videoStream) {
            videoStream.getTracks().forEach(track => track.stop());
            setVideoStream(null);
            setCameraStatus('idle');
            console.log("Camera stream stopped and cleaned up.");
        }
    }, [videoStream]);

    // Effect for cleanup: Stops the camera when the component unmounts
    useEffect(() => {
        return () => stopCamera();
    }, [stopCamera]);


    // Actual Camera Access Logic
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
            console.error("Camera access denied or failed.", error);
        }
    };


    // Mock verification logic
    const handleVerify = (e) => {
        e.preventDefault();
        setIsLoading(true);
        setVerificationResult(null);

        // Mock verification delay
        setTimeout(() => {
            setIsLoading(false);
            if (certId.toLowerCase().includes('valid')) {
                setVerificationResult({
                    status: 'Verified',
                    name: 'Jane Doe',
                    certificate: 'Cloud Security Expert',
                    issueDate: '2025-05-10',
                    authority: 'TechCert Global',
                });
            } else if (certId.toLowerCase().includes('expired')) {
                setVerificationResult({
                    status: 'Expired',
                    name: 'John Smith',
                    certificate: 'Data Analysis Professional',
                    issueDate: '2022-01-01',
                    expiryDate: '2024-01-01',
                    authority: 'Data Guild',
                });
            } else {
                setVerificationResult({ status: 'NotFound' });
            }
        }, 1500);
    };

    const renderResult = () => {
        if (!verificationResult) return null;

        const { status, name, certificate, issueDate, expiryDate, authority } = verificationResult;

        const statusClasses = {
            Verified: 'bg-green-100 text-green-800 border-green-400',
            Expired: 'bg-yellow-100 text-yellow-800 border-yellow-400',
            NotFound: 'bg-red-100 text-red-800 border-red-400',
        };

        const statusText = {
            Verified: 'VERIFIED: This certificate is authentic and active.',
            Expired: 'EXPIRED: This certificate is authentic but has expired.',
            NotFound: 'NOT FOUND: No matching active certificate found for this ID.',
        };

        return (
            <div className={`mt-8 p-6 rounded-lg border-l-4 shadow-md ${statusClasses[status] || 'bg-gray-100 text-gray-800 border-gray-400'}`}>
                <h3 className="text-xl font-bold mb-3">{statusText[status]}</h3>
                {status !== 'NotFound' && (
                    <div className="space-y-2 text-sm">
                        <p><strong>Holder Name:</strong> {name}</p>
                        <p><strong>Credential:</strong> {certificate}</p>
                        <p><strong>Issuing Authority:</strong> {authority}</p>
                        <p><strong>Issue Date:</strong> {issueDate}</p>
                        {expiryDate && <p><strong>Expiry Date:</strong> {expiryDate}</p>}
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
                        {/* PDF Upload Box */}
                        <div className="border-2 border-dashed border-indigo-300 p-8 rounded-xl text-center bg-indigo-50 hover:bg-indigo-100 transition duration-150 cursor-pointer">
                            <input 
                                type="file" 
                                accept=".pdf" 
                                className="hidden" 
                                id="pdf-upload"
                                onChange={(e) => console.log('PDF selected:', e.target.files[0].name)}
                            />
                            <label htmlFor="pdf-upload" className="block cursor-pointer">
                                <svg xmlns="http://www.w3.org/2000/svg" className="mx-auto h-10 w-10 text-indigo-500 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 014 4v2a4 4 0 00-3.5-3.966M16 12h2a2 2 0 012 2v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5a2 2 0 012-2h2m4-7v12m0 0l-4-4m4 4l4-4" />
                                </svg>
                                <p className="text-gray-700 font-semibold">Click or drag a PDF file here</p>
                                <p className="text-sm text-gray-500 mt-1">Accepts only .pdf certificates for verification.</p>
                            </label>
                        </div>
                        <button 
                            type="button" 
                            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3 rounded-lg transition duration-150 shadow-lg"
                            onClick={() => console.log("Mock: Processing PDF...")}
                        >
                            Process PDF Verification
                        </button>
                    </div>
                );
            case 'camera':
                return (
                    <div className="space-y-6 text-center">
                        {/* Camera Access/Scanning Area */}
                        <div className="p-1 border-4 border-dashed border-gray-300 rounded-xl bg-black h-96 flex flex-col items-center justify-center relative overflow-hidden">
                            {cameraStatus === 'active' ? (
                                <>
                                    {/* The video element for the live stream */}
                                    <video 
                                        ref={videoRef} 
                                        autoPlay 
                                        playsInline 
                                        className="w-full h-full object-cover rounded-lg"
                                        onLoadedMetadata={() => videoRef.current.play()}
                                    />
                                    {/* QR Code Overlay Simulation */}
                                    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                                        <div className="w-3/4 h-3/4 border-4 border-green-500 rounded-lg animate-pulse" style={{boxShadow: '0 0 0 9999px rgba(0,0,0,0.5)'}}></div>
                                        <p className="absolute text-white bottom-4 font-semibold text-lg bg-black bg-opacity-50 px-3 py-1 rounded">Scanning Live Feed...</p>
                                    </div>
                                </>
                            ) : cameraStatus === 'idle' ? (
                                <p className="text-gray-400 font-medium">Click the button below to start the camera and scan a QR code.</p>
                            ) : cameraStatus === 'requested' ? (
                                <p className="text-indigo-400 animate-pulse font-medium">Awaiting camera permission...</p>
                            ) : ( // cameraStatus === 'error'
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
                // Manual Input Box
                return (
                    <form onSubmit={handleVerify} className="space-y-6">
                        <div>
                            <label htmlFor="cert-id" className="block text-sm font-medium text-gray-700 mb-1">Certificate ID</label>
                            <input
                                type="text"
                                id="cert-id"
                                className={INPUT_CLASS}
                                placeholder="e.g., TECH-2024-VALID-12345"
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
            {/* Card width increased to accommodate three tabs */}
            <div className={CARD_CLASS.replace('max-w-md', 'max-w-2xl')}> 
                <h2 className="text-3xl font-extrabold text-center text-indigo-700 mb-2">
                    Public Certificate Verification
                </h2>
                <p className="text-center text-gray-500 mb-8">
                    Choose a method to verify the authenticity of your document.
                </p>

                {/* Mode Selector Tabs */}
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
                        label="PDF Upload"
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

const LoginPage = ({ setView, setIsAuthenticated }) => {
    const handleSubmit = (e) => {
        e.preventDefault();
        // Mock authentication success
        setIsAuthenticated(true);
        setView('dashboard'); // Navigate to dashboard after login
    };

    return (
        // Wrapper to center the card vertically and horizontally within its parent
        <div className="flex items-center justify-center w-full flex-grow py-12">
            <div className={CARD_CLASS}>
                <h2 className="text-3xl font-extrabold text-center text-blue-700 mb-2">
                    Verification Portal Login
                </h2>
                <p className="text-center text-gray-500 mb-8">Sign in to manage your certificates.</p>

                <form onSubmit={handleSubmit} className="space-y-6">
                    <div>
                        <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">Email address</label>
                        <input type="text" id="email" className={INPUT_CLASS} placeholder="user@example.com" required />
                    </div>
                    
                    <div>
                        <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                        <input type="password" id="password" className={INPUT_CLASS} placeholder="••••••••" required />
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

                    <button type="submit" className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 rounded-lg transition duration-150 shadow-lg">
                        Log In
                    </button>
                </form>
                
                {/* REMOVED: Public Verification Button 
                <button 
                    type="button" 
                    className="w-full mt-4 bg-indigo-500 hover:bg-indigo-600 text-white font-semibold py-3 rounded-lg transition duration-150 shadow-lg"
                    onClick={() => setView('public')}
                >
                    Public Verification Portal
                </button>
                */}


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

const RegisterPage = ({ setView }) => {
    const handleSubmit = (e) => {
        e.preventDefault();
        // Mock registration, redirects to login
        setView('login');
    };

    return (
        <div className="flex items-center justify-center w-full flex-grow py-12">
            <div className={CARD_CLASS}>
                <h2 className="text-3xl font-extrabold text-center text-green-700 mb-2">
                    Create Account
                </h2>
                <p className="text-center text-gray-500 mb-8">Join the certification management platform.</p>
                <form onSubmit={handleSubmit} className="space-y-6">
                    <div>
                        <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                        <input type="text" id="username" className={INPUT_CLASS} placeholder="Your Name" required />
                    </div>
                    
                    <div>
                        <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                        <input type="email" id="email" className={INPUT_CLASS} placeholder="user@example.com" required />
                    </div>
                    
                    <div>
                        <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                        <input type="password" id="password" className={INPUT_CLASS} placeholder="••••••••" required />
                    </div>
                    
                    <button type="submit" className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-3 rounded-lg transition duration-150 shadow-lg mt-6">
                        Register
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

const ForgotPassword = ({ setView }) => {
    const handleSubmit = (e) => {
        e.preventDefault();
        // Use custom message box instead of alert()
        console.log("Password reset link sent (mock)");
        setView('login');
    };

    return (
        <div className="flex items-center justify-center w-full flex-grow py-12">
            <div className={CARD_CLASS}>
                <h2 className="text-3xl font-extrabold text-center text-purple-700 mb-2">
                    Password Reset
                </h2>
                <p className="text-center text-gray-500 mb-8">Enter your email to receive a password reset link.</p>
                
                <form onSubmit={handleSubmit} className="space-y-6">
                    <div>
                        <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">Email address</label>
                        <input type="email" id="email" className={INPUT_CLASS} placeholder="user@example.com" required />
                    </div>
                    
                    <button type="submit" className="w-full bg-purple-600 hover:bg-purple-700 text-white font-semibold py-3 rounded-lg transition duration-150 shadow-lg mt-6">
                        Send Reset Link
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


const UserDashboard = () => {
    const { userId, isAuthReady } = useAuthAndDb();
    
    // Mock Data
    const mockCertificates = [
        { id: 1, name: "Data Science Mastery", issueDate: "2023-08-15", status: "Verified" },
        { id: 2, name: "Web Development Pro", issueDate: "2024-01-20", status: "Pending" },
        { id: 3, name: "Cloud Architect Associate", issueDate: "2023-11-01", status: "Rejected" },
    ];

    if (!isAuthReady) return <div className="loading-state">Loading user data...</div>;

    return (
        // The dashboard is now centered using mx-auto and max-w-4xl
        <div className="p-4 sm:p-8 w-full max-w-4xl mx-auto"> 
            <h1 className="text-3xl font-bold mb-4 text-center text-gray-800">My Certificate Dashboard</h1>
            
            {/* Centered User ID Display */}
            <div className="text-center mb-6 p-3 bg-gray-100 rounded-lg max-w-lg mx-auto">
                <p className="text-sm font-medium text-gray-500">
                    User ID: <span className="font-mono text-gray-700 select-all break-words">{userId || 'N/A'}</span>
                </p>
            </div>

            <div className="bg-white p-6 sm:p-8 rounded-xl shadow-xl border border-gray-200">
                <div className="flex flex-col sm:flex-row justify-between items-center mb-6 pb-4 border-b border-gray-100">
                    <h2 className="text-2xl font-semibold text-gray-700 mb-3 sm:mb-0">Submitted Certificates</h2>
                    
                    <div className="flex space-x-4"> 
                        <button className="px-4 py-2 text-sm bg-gray-200 text-gray-700 font-semibold rounded-lg hover:bg-gray-300 transition duration-150 shadow-sm">
                            <span className="hidden sm:inline">Upload </span>New Certificate
                        </button>
                        <button className="px-4 py-2 text-sm bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition duration-150 shadow-md">
                            View Reports
                        </button>
                    </div>
                </div>

                {/* Responsive Table for Certificates */}
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Certificate Name</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Issue Date</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider w-48">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {mockCertificates.map(cert => (
                                <tr key={cert.id} className="hover:bg-blue-50 transition duration-150">
                                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{cert.name}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{cert.issueDate}</td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                                            cert.status === 'Verified' ? 'bg-green-100 text-green-800' :
                                            cert.status === 'Pending' ? 'bg-yellow-100 text-yellow-800' :
                                            'bg-red-100 text-red-800'
                                        }`}>
                                            {cert.status}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                                        <div className="flex justify-center space-x-2">
                                            <button className="text-xs px-3 py-1 bg-indigo-500 text-white rounded-md hover:bg-indigo-600 transition duration-150">
                                                View
                                            </button>
                                            <button className="text-xs px-3 py-1 bg-red-500 text-white rounded-md hover:bg-red-600 transition duration-150">
                                                Delete
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
            
            <div className="text-center mt-6 p-4 bg-yellow-50 text-yellow-800 rounded-lg shadow-inner max-w-4xl mx-auto text-sm">
                <p>Note: Certificates with 'Pending' status are currently under review by the authority.</p>
            </div>
        </div>
    );
};


/**
 * MAIN APPLICATION COMPONENT
 */
const App = () => {
    // Initial view is set to 'login' as requested.
    const [view, setView] = useState('login'); 
    const [isAuthenticated, setIsAuthenticated] = useState(false);

    // Simple navigation function
    const navigateTo = (newView) => {
        setView(newView);
    };

    const renderContent = () => {
        // Unauthenticated views
        if (!isAuthenticated) {
            switch (view) {
                case 'register':
                    return <RegisterPage setView={navigateTo} />;
                case 'forgot-password':
                    return <ForgotPassword setView={navigateTo} />;
                case 'public': // Public portal is now a separate, unauthenticated page
                    return <PublicVerificationPortal setView={navigateTo} />;
                case 'login':
                default:
                    return <LoginPage setView={navigateTo} setIsAuthenticated={setIsAuthenticated} />;
            }
        }
        
        // Authenticated users
        switch (view) {
            case 'public': // Allow authenticated users to view public portal too
                return <PublicVerificationPortal setView={navigateTo} />;
            case 'dashboard':
            default:
                return <UserDashboard />;
        }
    };

    return (
        // Global Centering and Full Screen Background
        <div className="flex flex-col items-center justify-center bg-gray-50 min-h-screen w-full p-4 sm:p-8 font-sans">
            <div className="w-full max-w-6xl">
                <div className="w-full"> 
                    
                    {/* Header/Navigation Area */}
                    <header className="flex justify-end p-4 sm:p-6 pb-2">
                        <div className='flex space-x-4 items-center'>
                            {!isAuthenticated ? (
                                <>
                                    {/* Public Verification Link in Header (The only way to access it now) */}
                                    {view !== 'public' && view !== 'login' && view !== 'register' && view !== 'forgot-password' && (
                                        <button
                                            onClick={() => navigateTo('public')}
                                            className="px-4 py-2 text-indigo-600 font-semibold rounded-lg hover:bg-indigo-50 transition duration-150 border border-indigo-600"
                                        >
                                            Public Verification
                                        </button>
                                    )}
                                    
                                    {/* Show Log In button only if not currently on Login or Register pages */}
                                    {(view !== 'login' && view !== 'register' && view !== 'forgot-password') && (
                                        <button
                                            onClick={() => navigateTo('login')}
                                            className="px-4 py-2 text-blue-600 font-semibold rounded-lg hover:bg-blue-50 transition duration-150 border border-blue-600"
                                        >
                                            Log In
                                        </button>
                                    )}
                                </>
                            ) : (
                                // Authenticated Navigation
                                <>
                                    {view !== 'dashboard' && (
                                        <button 
                                            onClick={() => navigateTo('dashboard')}
                                            className="px-4 py-2 text-gray-600 font-semibold rounded-lg hover:bg-gray-100 transition duration-150"
                                        >
                                            Dashboard
                                        </button>
                                    )}
                                    
                                    {view !== 'public' && (
                                        <button 
                                            onClick={() => navigateTo('public')}
                                            className="px-4 py-2 text-indigo-600 font-semibold rounded-lg hover:bg-indigo-50 transition duration-150 border border-indigo-600"
                                        >
                                            Public Verification
                                        </button>
                                    )}
                                    
                                    <button 
                                        onClick={() => {
                                            setIsAuthenticated(false);
                                            navigateTo('login'); // Redirect to login on logout
                                        }}
                                        className='px-6 py-2 bg-red-500 text-white font-semibold rounded-lg shadow-md hover:bg-red-600 transition duration-150'
                                    >
                                        Logout
                                    </button>
                                </>
                            )}
                        </div>
                    </header>
                    
                    {/* Main Content Rendered Here - always centered */}
                    <main className="flex-grow flex flex-col justify-center items-center">
                        {renderContent()}
                    </main>

                </div>
            </div>
        </div>
    );
};

export default App;
