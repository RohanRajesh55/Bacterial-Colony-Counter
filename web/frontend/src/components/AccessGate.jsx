import { useState, useEffect } from 'react';

/**
 * Access Gate Component
 * Protects the app with a simple access code.
 * Users with the link need to enter the code once, which is stored in localStorage.
 */

// You can change this access code to whatever you want
// For production, consider using environment variables
const ACCESS_CODE = 'syntech2026';

function AccessGate({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [inputCode, setInputCode] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  // Check if user has already authenticated
  useEffect(() => {
    const storedAuth = localStorage.getItem('cfu_access_authenticated');
    const storedCode = localStorage.getItem('cfu_access_code');
    
    if (storedAuth === 'true' && storedCode === ACCESS_CODE) {
      setIsAuthenticated(true);
    }
    setIsLoading(false);
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    
    if (inputCode.trim() === ACCESS_CODE) {
      localStorage.setItem('cfu_access_authenticated', 'true');
      localStorage.setItem('cfu_access_code', ACCESS_CODE);
      setIsAuthenticated(true);
      setError('');
    } else {
      setError('Invalid access code. Please check and try again.');
      setInputCode('');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('cfu_access_authenticated');
    localStorage.removeItem('cfu_access_code');
    setIsAuthenticated(false);
  };

  // Expose logout function globally for the app to use
  useEffect(() => {
    window.cfuLogout = handleLogout;
  }, []);

  if (isLoading) {
    return (
      <div className="access-gate-loading">
        <div className="spinner" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="access-gate">
        <div className="access-gate-card">
          <div className="access-gate-header">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="access-gate-icon">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
              <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
            </svg>
            <h1>CFU-Counter</h1>
            <p>Private Access Required</p>
          </div>
          
          <form onSubmit={handleSubmit} className="access-gate-form">
            <div className="access-gate-input-group">
              <label htmlFor="accessCode">Access Code</label>
              <input
                id="accessCode"
                type="password"
                value={inputCode}
                onChange={(e) => setInputCode(e.target.value)}
                placeholder="Enter your access code"
                autoFocus
                autoComplete="off"
              />
            </div>
            
            {error && (
              <div className="access-gate-error">
                {error}
              </div>
            )}
            
            <button type="submit" className="access-gate-submit">
              Access Application
            </button>
          </form>
          
          <p className="access-gate-footer">
            Contact the administrator if you need access.
          </p>
        </div>
      </div>
    );
  }

  return children;
}

export default AccessGate;
