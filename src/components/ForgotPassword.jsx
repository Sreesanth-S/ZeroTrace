import React, { useState } from 'react';

const ForgotPassword = ({ setView }) => {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [isSubmitted, setIsSubmitted] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    // Here you would typically make an API call to send a reset password email
    console.log('Password reset requested for:', email);
    setMessage('Password reset link has been sent to your email.');
    setIsSubmitted(true);
  };

  if (isSubmitted) {
    return (
      <div className="forgot-password-container">
        <h2>Reset Password</h2>
        <div className="success-message">
          <p>{message}</p>
          <button onClick={() => setView('login')} className="back-to-login">
            Back to Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="forgot-password-container">
      <h2>Reset Password</h2>
      <p>Enter your email address to receive a password reset link.</p>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="email">Email Address</label>
          <input
            type="email"
            id="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Enter your email address"
            required
          />
        </div>
        <div className="form-actions">
          <button type="submit" className="reset-button">Send Reset Link</button>
          <button type="button" onClick={() => setView('login')} className="cancel-button">
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
};

export default ForgotPassword;