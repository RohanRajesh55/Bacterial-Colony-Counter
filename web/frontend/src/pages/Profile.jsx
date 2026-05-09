import { useState, useEffect } from 'react';

function Profile() {
  const [activeTab, setActiveTab] = useState('profile');
  const [settings, setSettings] = useState(() => {
    const saved = localStorage.getItem('userSettings');
    return saved ? JSON.parse(saved) : {
      defaultModel: 'yolo',
      showBoundingBoxes: true,
      confidenceThreshold: 0.40,
      darkMode: false,
      notifications: true,
      // Report Settings
      labName: '',
      researcherName: '',
      // Visual Settings
      boxColor: '#00FF00', // Neon Green default
      boxOpacity: 0.8,
    };
  });

  // Apply dark mode on mount and when setting changes
  useEffect(() => {
    if (settings.darkMode) {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
  }, [settings.darkMode]);

  const handleSettingChange = (key, value) => {
    const newSettings = { ...settings, [key]: value };
    setSettings(newSettings);
    localStorage.setItem('userSettings', JSON.stringify(newSettings));
    
    // Dispatch custom event for immediate dark mode updates
    window.dispatchEvent(new Event('settingsUpdated'));
  };

  return (
    <div className="profile-page">
      <div className="profile-header">
        <h1>Account</h1>
        <p>Manage your profile and preferences</p>
      </div>

      <div className="profile-tabs">
        <button 
          className={`profile-tab ${activeTab === 'profile' ? 'active' : ''}`}
          onClick={() => setActiveTab('profile')}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
            <circle cx="12" cy="7" r="4"></circle>
          </svg>
          Profile
        </button>
        <button 
          className={`profile-tab ${activeTab === 'settings' ? 'active' : ''}`}
          onClick={() => setActiveTab('settings')}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
          </svg>
          Settings
        </button>
      </div>

      <div className="profile-content">
        {activeTab === 'profile' && (
          <div className="profile-section">
            <div className="profile-avatar-section">
              <div className="profile-avatar">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                  <circle cx="12" cy="7" r="4"></circle>
                </svg>
              </div>
              <div className="profile-avatar-info">
                <h3>Guest User</h3>
                <p>Using CFU-Counter locally</p>
              </div>
            </div>

            <div className="profile-stats">
              <div className="stat-card stat-accent-teal">
                <span className="stat-number">-</span>
                <span className="stat-label">Total Analyses</span>
              </div>
              <div className="stat-card stat-accent-orange">
                <span className="stat-number">-</span>
                <span className="stat-label">Colonies Detected</span>
              </div>
              <div className="stat-card stat-accent-blue">
                <span className="stat-number">7</span>
                <span className="stat-label">Species Supported</span>
              </div>
            </div>

            <div className="profile-info-card">
              <h3>About CFU-Counter</h3>
              <p>
                CFU-Counter is an AI-powered bacterial colony counter and classifier. 
                It uses YOLOv8 for object detection and a CNN for classification, 
                capable of identifying 7 different bacterial species.
              </p>
              <div className="profile-badges">
                <span className="badge badge-teal">YOLOv8</span>
                <span className="badge badge-orange">CNN</span>
                <span className="badge badge-blue">FastAPI</span>
                <span className="badge badge-teal">React</span>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="settings-section">
            <div className="settings-group">
              <h3>Analysis Defaults</h3>
              
              <div className="setting-item">
                <div className="setting-info">
                  <span className="setting-label">Default Model</span>
                  <span className="setting-desc">Choose the default model for analysis</span>
                </div>
                <select 
                  value={settings.defaultModel}
                  onChange={(e) => handleSettingChange('defaultModel', e.target.value)}
                  className="setting-select"
                >
                  <option value="yolo">YOLO (Detection)</option>
                  <option value="cnn">CNN (Classification)</option>
                </select>
              </div>

              <div className="setting-item">
                <div className="setting-info">
                  <span className="setting-label">Show Bounding Boxes</span>
                  <span className="setting-desc">Display boxes around detected colonies</span>
                </div>
                <div 
                  className={`toggle ${settings.showBoundingBoxes ? 'active' : ''}`}
                  onClick={() => handleSettingChange('showBoundingBoxes', !settings.showBoundingBoxes)}
                >
                  <div className="toggle-knob" />
                </div>
              </div>

              <div className="setting-item">
                <div className="setting-info">
                  <span className="setting-label">Confidence Threshold</span>
                  <span className="setting-desc">Minimum confidence for detection ({(settings.confidenceThreshold * 100).toFixed(0)}%)</span>
                </div>
                <input 
                  type="range"
                  min="0.1"
                  max="0.9"
                  step="0.05"
                  value={settings.confidenceThreshold}
                  onChange={(e) => handleSettingChange('confidenceThreshold', parseFloat(e.target.value))}
                  className="setting-slider"
                />
              </div>
            </div>

            <div className="settings-group">
              <h3>Report Settings</h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: 'var(--spacing-md)' }}>
                These details will appear on your exported PDF reports
              </p>
              
              <div className="report-settings-card" style={{
                background: 'var(--bg-primary)',
                borderRadius: 'var(--radius-md)',
                padding: 'var(--spacing-lg)',
                border: '1px solid var(--border-color)'
              }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-lg)' }}>
                  <div className="form-group">
                    <label className="form-label" style={{
                      display: 'block',
                      fontWeight: '600',
                      marginBottom: 'var(--spacing-xs)',
                      color: 'var(--text-primary)',
                      fontSize: '0.875rem'
                    }}>
                      🏢 Lab / Institution
                    </label>
                    <input 
                      type="text" 
                      value={settings.labName}
                      onChange={(e) => handleSettingChange('labName', e.target.value)}
                      placeholder="e.g. Microbiology Dept"
                      className="setting-input"
                      style={{
                        width: '100%',
                        padding: 'var(--spacing-sm) var(--spacing-md)',
                        border: '1px solid var(--border-color)',
                        borderRadius: 'var(--radius-sm)',
                        fontSize: '0.9rem',
                        background: 'var(--bg-card)',
                        color: 'var(--text-primary)'
                      }}
                    />
                  </div>
                  
                  <div className="form-group">
                    <label className="form-label" style={{
                      display: 'block',
                      fontWeight: '600',
                      marginBottom: 'var(--spacing-xs)',
                      color: 'var(--text-primary)',
                      fontSize: '0.875rem'
                    }}>
                      👤 Researcher Name
                    </label>
                    <input 
                      type="text" 
                      value={settings.researcherName}
                      onChange={(e) => handleSettingChange('researcherName', e.target.value)}
                      placeholder="e.g. Dr. Jane Doe"
                      className="setting-input"
                      style={{
                        width: '100%',
                        padding: 'var(--spacing-sm) var(--spacing-md)',
                        border: '1px solid var(--border-color)',
                        borderRadius: 'var(--radius-sm)',
                        fontSize: '0.9rem',
                        background: 'var(--bg-card)',
                        color: 'var(--text-primary)'
                      }}
                    />
                  </div>
                </div>
                
                {(settings.labName || settings.researcherName) && (
                  <div style={{
                    marginTop: 'var(--spacing-md)',
                    padding: 'var(--spacing-sm) var(--spacing-md)',
                    background: 'var(--accent-primary-bg)',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '0.8rem',
                    color: 'var(--text-secondary)'
                  }}>
                    ✓ Report will show: <strong>{settings.labName || 'No lab name'}</strong> — <strong>{settings.researcherName || 'No researcher'}</strong>
                  </div>
                )}
              </div>
            </div>

            <div className="settings-group">
              <h3>Visual Customization</h3>
              
              <div className="setting-item">
                <div className="setting-info">
                  <span className="setting-label">Bounding Box Color</span>
                  <span className="setting-desc">Color for detected colonies</span>
                </div>
                <div className="color-picker-wrapper">
                   <input 
                    type="color" 
                    value={settings.boxColor}
                    onChange={(e) => handleSettingChange('boxColor', e.target.value)}
                    className="color-picker"
                  />
                  <span className="color-value">{settings.boxColor}</span>
                </div>
              </div>

              <div className="setting-item">
                <div className="setting-info">
                  <span className="setting-label">Overlay Opacity</span>
                  <span className="setting-desc">Transparency of boxes ({(settings.boxOpacity * 100).toFixed(0)}%)</span>
                </div>
                <input 
                  type="range"
                  min="0.1"
                  max="1.0"
                  step="0.1"
                  value={settings.boxOpacity}
                  onChange={(e) => handleSettingChange('boxOpacity', parseFloat(e.target.value))}
                  className="setting-slider"
                />
              </div>
            </div>

            <div className="settings-group">
              <h3>Appearance</h3>
              
              <div className="setting-item">
                <div className="setting-info">
                  <span className="setting-label">Dark Mode</span>
                  <span className="setting-desc">Switch between light and dark themes</span>
                </div>
                <div 
                  className={`toggle ${settings.darkMode ? 'active' : ''}`}
                  onClick={() => handleSettingChange('darkMode', !settings.darkMode)}
                >
                  <div className="toggle-knob" />
                </div>
              </div>
            </div>

            <div className="settings-group">
              <h3>Data</h3>
              
              <div className="setting-item">
                <div className="setting-info">
                  <span className="setting-label">Clear History</span>
                  <span className="setting-desc">Remove all saved analysis history</span>
                </div>
                <button 
                  className="btn btn-danger-outline"
                  onClick={() => {
                    localStorage.removeItem('analysisHistory');
                    alert('History cleared!');
                  }}
                >
                  Clear
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default Profile;
