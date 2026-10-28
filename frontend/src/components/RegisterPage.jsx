import React, { useState } from 'react';
import { supabase } from '../lib/supabase';

const RegisterPage = ({ setView }) => {
  const [formData, setFormData] = useState({
    fullName: '',
    email: '',
    password: '',
    confirmPassword: '',
    agreed: false,
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData({ ...formData, [name]: type === 'checkbox' ? checked : value });
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (formData.password !== formData.confirmPassword) {
      setError("Passwords don't match!");
      return;
    }

    if (formData.password.length < 6) {
      setError("Password must be at least 6 characters long.");
      return;
    }

    setIsLoading(true);
    try {
      const { data, error: signUpError } = await supabase.auth.signUp({
        email: formData.email.trim(),
        password: formData.password,
        options: {
          data: {
            full_name: formData.fullName.trim(),
          },
        },
      });

      if (signUpError) throw signUpError;

      if (data.session) {
        setSuccess("Account created successfully!");
        setTimeout(() => setView && setView('dashboard'), 1500);
      } else if (data.user) {
        setSuccess("Account created! Please check your email to confirm your account, then log in.");
      }
    } catch (err) {
      setError(err.message || 'Registration failed.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="register-container p-6 max-w-md mx-auto bg-white rounded shadow-md border my-8">
      <h2 className="text-xl font-bold mb-4 text-center">Create Your Account</h2>
      {success && (
        <div className="mb-4 text-sm text-green-700 bg-green-50 p-2 rounded border border-green-200">
          {success}
        </div>
      )}
      {error && (
        <div className="mb-4 text-sm text-red-600 bg-red-50 p-2 rounded border border-red-200">
          {error}
        </div>
      )}
      <form onSubmit={handleRegister} className="space-y-3">
        <div className="form-group">
          <label htmlFor="fullName" className="block text-sm font-medium mb-1">Full Name</label>
          <input
            type="text"
            id="fullName"
            name="fullName"
            value={formData.fullName}
            onChange={handleChange}
            placeholder="e.g., John Doe"
            className="w-full p-2 border rounded"
            required
          />
        </div>
        <div className="form-group">
          <label htmlFor="email" className="block text-sm font-medium mb-1">Email Address</label>
          <input
            type="email"
            id="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            placeholder="e.g., john.doe@example.com"
            className="w-full p-2 border rounded"
            required
          />
        </div>
        <div className="form-group">
          <label htmlFor="password" className="block text-sm font-medium mb-1">Password</label>
          <input
            type="password"
            id="password"
            name="password"
            value={formData.password}
            onChange={handleChange}
            placeholder="Minimum 6 characters"
            className="w-full p-2 border rounded"
            required
          />
        </div>
        <div className="form-group">
          <label htmlFor="confirmPassword" className="block text-sm font-medium mb-1">Confirm Password</label>
          <input
            type="password"
            id="confirmPassword"
            name="confirmPassword"
            value={formData.confirmPassword}
            onChange={handleChange}
            placeholder="Re-enter your password"
            className="w-full p-2 border rounded"
            required
          />
        </div>
        <div className="form-group checkbox-group flex items-center gap-2 pt-2">
          <input
            type="checkbox"
            id="agreed"
            name="agreed"
            checked={formData.agreed}
            onChange={handleChange}
            required
          />
          <label htmlFor="agreed" className="text-xs text-gray-600">
            I agree to the Terms of Service and Privacy Policy
          </label>
        </div>
        <button
          type="submit"
          disabled={isLoading}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 rounded font-semibold disabled:opacity-50 mt-4"
        >
          {isLoading ? 'Creating...' : 'Create Account'}
        </button>
      </form>
      <div className="mt-4 text-center text-sm">
        <p>
          Already have an account?{' '}
          <button onClick={() => setView && setView('login')} className="text-blue-600 hover:underline font-medium">
            Log in
          </button>
        </p>
      </div>
    </div>
  );
};

export default RegisterPage;