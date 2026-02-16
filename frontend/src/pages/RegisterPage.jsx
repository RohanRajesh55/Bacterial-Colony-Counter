import { useState } from 'react';
import { useNavigate, Link } from 'react-router';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

function RegisterPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email, password })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Registration failed');
      }

      setSuccess(true);
      setTimeout(() => {
        navigate('/login');
      }, 2000);
    } catch (err) {
      setError(err.message || 'Registration failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (success) {
    return (
      <div className="auth-page">
        <div className="card auth-card">
          <h2 className="card-title">Registration Successful</h2>
          <p style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>
            Your account has been created. Redirecting to login...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <div className="card auth-card">
        <h2 className="card-title">Register</h2>

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              placeholder="Enter your email"
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="new-password"
              placeholder="At least 8 characters"
            />
          </div>

          <div className="form-group">
            <label htmlFor="confirmPassword">Confirm Password</label>
            <input
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              autoComplete="new-password"
              placeholder="Confirm your password"
            />
          </div>

          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

          <button
            type="submit"
            className="btn btn-primary"
            disabled={isSubmitting}
            style={{ width: '100%' }}
          >
            {isSubmitting ? (
              <>
                <span className="spinner" style={{ width: 20, height: 20, borderWidth: 2 }} />
                Creating account...
              </>
            ) : (
              'Register'
            )}
          </button>
        </form>

        <div className="auth-links">
          <p>
            Already have an account? <Link to="/login">Login</Link>
          </p>
        </div>
      </div>
    </div>
  );
}

export default RegisterPage;
