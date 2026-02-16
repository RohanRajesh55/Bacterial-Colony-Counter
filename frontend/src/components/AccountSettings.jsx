import { useState } from 'react';
import { useAuth } from '../context/AuthContext';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

function AccountSettings() {
  const { user } = useAuth();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    // Validation
    if (newPassword.length < 8) {
      setError('New password must be at least 8 characters');
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('New passwords do not match');
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/account/password`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to change password');
      }

      setSuccess('Password changed successfully');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err) {
      setError(err.message || 'Failed to change password');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="account-section">
      <h3>Account Information</h3>
      <div className="form-group" style={{ marginBottom: 'var(--spacing-xl)' }}>
        <label>Email</label>
        <input
          type="email"
          value={user?.email || ''}
          disabled
          className="form-input"
          style={{ backgroundColor: 'var(--bg-glass)', cursor: 'not-allowed' }}
        />
      </div>

      <h3>Change Password</h3>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="current-password">Current Password</label>
          <input
            id="current-password"
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            required
            className="form-input"
            placeholder="Enter current password"
          />
        </div>

        <div className="form-group">
          <label htmlFor="new-password">New Password</label>
          <input
            id="new-password"
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
            minLength={8}
            className="form-input"
            placeholder="Enter new password (min 8 characters)"
          />
        </div>

        <div className="form-group">
          <label htmlFor="confirm-password">Confirm New Password</label>
          <input
            id="confirm-password"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            minLength={8}
            className="form-input"
            placeholder="Confirm new password"
          />
        </div>

        {error && (
          <div className="error-message" style={{ marginBottom: 'var(--spacing-md)' }}>
            {error}
          </div>
        )}

        {success && (
          <div className="success-message" style={{ marginBottom: 'var(--spacing-md)' }}>
            {success}
          </div>
        )}

        <button
          type="submit"
          className="btn btn-primary"
          disabled={isSubmitting}
          style={{ width: 'auto' }}
        >
          {isSubmitting ? (
            <>
              <span className="spinner" style={{ width: 20, height: 20, borderWidth: 2 }} />
              Changing...
            </>
          ) : (
            'Change Password'
          )}
        </button>
      </form>
    </div>
  );
}

export default AccountSettings;
