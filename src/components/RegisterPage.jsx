import React, { useState } from 'react';

const RegisterPage = ({ setView }) => {
  const [formData, setFormData] = useState({
    fullName: '', email: '', password: '', confirmPassword: '', agreed: false,
  });

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData({ ...formData, [name]: type === 'checkbox' ? checked : value });
  };

  const handleRegister = (e) => {
    e.preventDefault();
    if (formData.password !== formData.confirmPassword) {
      alert("Passwords don't match!");
      return;
    }
    console.log('Registering user:', formData);
    // After successful registration, navigate to login page
    setView('login');
  };

  return (
    <div className="register-container">
      <h2>Create Your Account</h2>
      <form onSubmit={handleRegister}>
        <div className="form-group">
          <label htmlFor="fullName">Full Name</label>
          <input type="text" id="fullName" name="fullName" value={formData.fullName} onChange={handleChange} placeholder="e.g., John Doe" required />
        </div>
        <div className="form-group">
          <label htmlFor="email">Email Address</label>
          <input type="email" id="email" name="email" value={formData.email} onChange={handleChange} placeholder="e.g., john.doe@example.com" required />
        </div>
        <div className="form-group">
          <label htmlFor="password">Password</label>
          <input type="password" id="password" name="password" value={formData.password} onChange={handleChange} placeholder="Create a strong password" required />
        </div>
        <div className="form-group">
          <label htmlFor="confirmPassword">Confirm Password</label>
          <input type="password" id="confirmPassword" name="confirmPassword" value={formData.confirmPassword} onChange={handleChange} placeholder="Re-enter your password" required />
        </div>
        <div className="form-group checkbox-group">
          <input type="checkbox" id="agreed" name="agreed" checked={formData.agreed} onChange={handleChange} required />
          <label htmlFor="agreed">I agree to the Terms of Service and Privacy Policy</label>
        </div>
        <button type="submit" className="register-button">Create Account</button>
      </form>
    </div>
  );
};

export default RegisterPage;