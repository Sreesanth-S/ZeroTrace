import React, { useState } from 'react';

const LoginPage = ({ setView, setIsAuthenticated }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleLogin = (e) => {
    e.preventDefault();
    // Logic to handle user login, e.g., API call
    console.log('Logging in with:', { email, password });
    // After successful login, set authentication and navigate to dashboard
    setIsAuthenticated(true);
    setView('dashboard');
  };

  return (
    <div className='border flex items-center justify-center bg-gray-100'>
    <div className="w-96 p-6 bg-white rounded shadow-md">
      <h2>User Login</h2>
      <form onSubmit={handleLogin}>
        <div className="form-group">
          <label htmlFor="email">Email/Username</label>
          <input
            type="text"
            id="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Enter your email or username"
            required
          />
        </div>
        <div className="form-group">
          <label htmlFor="password">Password</label>
          <input
            type="password"
            id="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter your password"
            required
          />
        </div>
        <button type="submit" className="login-button">Login</button>
      </form>
      <div className="">
        <p><button onClick={() => setView('forgot-password')} className="forget-password">Forgot Password?</button></p>
        <p>Don't have an account? <button onClick={() => setView('register')} className="">Create an account</button></p>
      </div>
    </div>
    </div>
  );
};

export default LoginPage;