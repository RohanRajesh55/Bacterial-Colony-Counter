import { useState, useEffect } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

function APIKeyManager() {
  const [apiKeys, setApiKeys] = useState([]);
  const [newKeyName, setNewKeyName] = useState('');
  const [newKey, setNewKey] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isCreating, setIsCreating] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [copied, setCopied] = useState(false);

  const fetchApiKeys = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/api-keys`, {
        credentials: 'include'
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to fetch API keys');
      }

      const data = await response.json();
      setApiKeys(data);
    } catch (err) {
      setError(err.message || 'Failed to load API keys');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApiKeys();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!newKeyName.trim()) return;

    setIsCreating(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/api-keys`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({ name: newKeyName.trim() })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create API key');
      }

      const data = await response.json();
      setNewKey(data.key);
      setNewKeyName('');
      await fetchApiKeys();
    } catch (err) {
      setError(err.message || 'Failed to create API key');
    } finally {
      setIsCreating(false);
    }
  };

  const handleDelete = async (keyId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/api-keys/${keyId}`, {
        method: 'DELETE',
        credentials: 'include'
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to delete API key');
      }

      setDeleteConfirm(null);
      await fetchApiKeys();
    } catch (err) {
      setError(err.message || 'Failed to delete API key');
    }
  };

  const copyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = text;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Never';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  if (loading) {
    return (
      <div className="loading-overlay" style={{ padding: 'var(--spacing-xl)' }}>
        <div className="spinner" />
        <p className="loading-text">Loading API keys...</p>
      </div>
    );
  }

  return (
    <div className="account-section">
      <h3>API Keys</h3>
      <p style={{ color: 'var(--text-secondary)', marginBottom: 'var(--spacing-lg)', fontSize: '0.875rem' }}>
        Create API keys to access the colony counting API programmatically.
      </p>

      {/* New Key Display */}
      {newKey && (
        <div className="new-key-warning">
          <div style={{ fontWeight: 600, marginBottom: 'var(--spacing-sm)' }}>
            API Key Created Successfully
          </div>
          <p style={{ fontSize: '0.875rem', marginBottom: 'var(--spacing-md)' }}>
            Copy this key now. It will only be shown once!
          </p>
          <div className="api-key-value-container">
            <code className="api-key-value">{newKey}</code>
            <button
              className="copy-btn"
              onClick={() => copyToClipboard(newKey)}
            >
              {copied ? 'Copied!' : 'Copy'}
            </button>
          </div>
          <button
            className="btn btn-secondary"
            style={{ marginTop: 'var(--spacing-md)', width: 'auto' }}
            onClick={() => setNewKey(null)}
          >
            Done
          </button>
        </div>
      )}

      {/* Create Key Form */}
      <form onSubmit={handleCreate} style={{ marginBottom: 'var(--spacing-xl)' }}>
        <div style={{ display: 'flex', gap: 'var(--spacing-md)', alignItems: 'flex-end' }}>
          <div className="form-group" style={{ flex: 1, marginBottom: 0 }}>
            <label htmlFor="key-name">Key Name</label>
            <input
              id="key-name"
              type="text"
              value={newKeyName}
              onChange={(e) => setNewKeyName(e.target.value)}
              placeholder="e.g., Production Server"
              className="form-input"
              required
            />
          </div>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={isCreating || !newKeyName.trim()}
            style={{ width: 'auto', height: 'fit-content' }}
          >
            {isCreating ? (
              <>
                <span className="spinner" style={{ width: 20, height: 20, borderWidth: 2 }} />
                Creating...
              </>
            ) : (
              'Create Key'
            )}
          </button>
        </div>
      </form>

      {error && (
        <div className="error-message" style={{ marginBottom: 'var(--spacing-md)' }}>
          {error}
        </div>
      )}

      {/* API Keys List */}
      <h4 style={{ marginBottom: 'var(--spacing-md)', color: 'var(--text-secondary)' }}>
        Your API Keys
      </h4>

      {apiKeys.length === 0 ? (
        <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 'var(--spacing-lg)' }}>
          No API keys yet. Create one above.
        </p>
      ) : (
        <div className="api-keys-list">
          {apiKeys.map((key) => (
            <div key={key.id} className="api-key-item">
              <div className="api-key-info">
                <div className="api-key-name">{key.name}</div>
                <code className="api-key-prefix">{key.prefix}...</code>
                <div className="api-key-dates">
                  <span>Created: {formatDate(key.created_at)}</span>
                  <span>Last used: {formatDate(key.last_used_at)}</span>
                </div>
              </div>
              <div className="api-key-actions">
                {deleteConfirm === key.id ? (
                  <>
                    <button
                      className="btn-danger-sm"
                      onClick={() => handleDelete(key.id)}
                    >
                      Confirm
                    </button>
                    <button
                      className="btn-cancel-sm"
                      onClick={() => setDeleteConfirm(null)}
                    >
                      Cancel
                    </button>
                  </>
                ) : (
                  <button
                    className="btn-danger-sm"
                    onClick={() => setDeleteConfirm(key.id)}
                  >
                    Revoke
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default APIKeyManager;
