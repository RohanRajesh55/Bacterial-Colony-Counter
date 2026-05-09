import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getHistory, deleteHistory } from '../services/api';

function History() {
  const [history, setHistory] = useState([]);
  const [selectedEntry, setSelectedEntry] = useState(null);
  const [imageZoom, setImageZoom] = useState(false);
  const [zoomImage, setZoomImage] = useState(null);
  
  // Filter states
  const [searchQuery, setSearchQuery] = useState('');
  const [modelFilter, setModelFilter] = useState('all'); // 'all', 'yolo', 'cnn'
  const [dateFilter, setDateFilter] = useState('all'); // 'all', 'today', 'week', 'month'

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const data = await getHistory();
      setHistory(data);
      if (data.length > 0 && !selectedEntry) {
        setSelectedEntry(data[0]);
      }
    } catch (error) {
      console.error('Failed to load history:', error);
    }
  };

  const formatDate = (isoString) => {
    if (!isoString) return 'Unknown date';
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch (e) {
      return 'Unknown date';
    }
  };

  const clearHistory = () => {
    if (window.confirm('Clearing history via API is not yet supported in bulk. Delete items individually.')) {
      // API bulk delete not implemented yet
    }
  };

  const deleteEntry = async (id, e) => {
    e.stopPropagation();
    if (window.confirm('Delete this analysis?')) {
        try {
            await deleteHistory(id);
            const newHistory = history.filter(entry => entry.id !== id);
            setHistory(newHistory);
            if (selectedEntry?.id === id) {
             setSelectedEntry(newHistory.length > 0 ? newHistory[0] : null);
            }
        } catch (error) {
            console.error("Failed to delete", error);
        }
    }
  };

  const handleImageClick = (imageSrc) => {
    setZoomImage(imageSrc);
    setImageZoom(true);
  };

  const exportToCSV = () => {
    if (history.length === 0) return;
    
    const headers = ['Date', 'File Name', 'Model', 'Total Count', 'Confidence'];
    const rows = history.map(entry => [
      formatDate(entry.timestamp),
      entry.imageName || 'Unknown',
      (entry.modelType || 'unknown').toUpperCase(),
      entry.totalCount || 0,
      entry.confidenceThreshold ? `${(entry.confidenceThreshold * 100).toFixed(0)}%` : '40%'
    ]);
    
    const csvContent = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cfu-counter-history-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Filter logic
  const getFilteredHistory = () => {
    return history.filter(entry => {
      // Search filter (filename)
      if (searchQuery && !(entry.imageName || '').toLowerCase().includes(searchQuery.toLowerCase())) {
        return false;
      }
      
      // Model filter
      if (modelFilter !== 'all' && (entry.modelType || '').toLowerCase() !== modelFilter) {
        return false;
      }
      
      // Date filter
      if (dateFilter !== 'all' && entry.timestamp) {
        const entryDate = new Date(entry.timestamp);
        const now = new Date();
        const diffDays = Math.floor((now - entryDate) / (1000 * 60 * 60 * 24));
        
        if (dateFilter === 'today' && diffDays > 0) return false;
        if (dateFilter === 'week' && diffDays > 7) return false;
        if (dateFilter === 'month' && diffDays > 30) return false;
      }
      
      return true;
    });
  };
  
  const filteredHistory = getFilteredHistory();

  const formatImageSrc = (base64String) => {
    if (!base64String) return null;
    if (base64String.startsWith('data:image')) {
      return base64String;
    }
    return `data:image/jpeg;base64,${base64String}`;
  };

  if (history.length === 0) {
    return (
      <div className="history-page">
        <div className="page-header">
          <h1>Analysis History</h1>
          <p>Your past analysis results will appear here.</p>
        </div>
        <div className="empty-state" style={{ marginTop: 'var(--spacing-2xl)' }}>
          <svg className="empty-state-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <polyline points="12 6 12 12 16 14"></polyline>
          </svg>
          <p>No analysis history yet</p>
          <span style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: 'var(--spacing-md)' }}>
            Analyze a petri dish image to see your results here
          </span>
          <Link to="/analyzer" className="btn btn-primary" style={{ marginTop: 'var(--spacing-md)' }}>
            Start Analyzing
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="history-page">
      <div className="page-header">
        <h1>Analysis History</h1>
        <p>Review and compare your previous colony analysis results.</p>
      </div>

      <div className="history-layout">
        {/* History List */}
        <div className="history-list-container">
          {/* Filter Controls */}
          <div className="history-filters">
            <div className="filter-search">
              <svg style={{ width: 16, height: 16 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
              </svg>
              <input 
                type="text"
                placeholder="Search by filename..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="filter-input"
              />
            </div>
            <div className="filter-row">
              <select 
                value={modelFilter} 
                onChange={(e) => setModelFilter(e.target.value)}
                className="filter-select"
              >
                <option value="all">All Models</option>
                <option value="yolo">YOLO</option>
                <option value="cnn">CNN</option>
              </select>
              <select 
                value={dateFilter} 
                onChange={(e) => setDateFilter(e.target.value)}
                className="filter-select"
              >
                <option value="all">All Time</option>
                <option value="today">Today</option>
                <option value="week">Last 7 Days</option>
                <option value="month">Last 30 Days</option>
              </select>
            </div>
          </div>
          
          <div className="history-list-header">
            <span>{filteredHistory.length} of {history.length} {history.length === 1 ? 'analysis' : 'analyses'}</span>
            <div style={{ display: 'flex', gap: 'var(--spacing-sm)' }}>
              <button className="btn btn-secondary btn-sm" onClick={exportToCSV} title="Export to CSV">
                <svg style={{ width: 14, height: 14 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                  <polyline points="7 10 12 15 17 10"></polyline>
                  <line x1="12" y1="15" x2="12" y2="3"></line>
                </svg>
              </button>
              <button className="btn btn-secondary btn-sm" onClick={clearHistory} title="Clear All">
                <svg style={{ width: 14, height: 14 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="3 6 5 6 21 6"></polyline>
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                </svg>
              </button>
            </div>
          </div>
          <div className="history-list">
            {filteredHistory.length === 0 ? (
              <div className="filter-no-results">
                <svg style={{ width: 32, height: 32, opacity: 0.5 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
                </svg>
                <p>No results match your filters</p>
                <button className="btn btn-secondary btn-sm" onClick={() => { setSearchQuery(''); setModelFilter('all'); setDateFilter('all'); }}>
                  Clear Filters
                </button>
              </div>
            ) : filteredHistory.map((entry) => (
              <div
                key={entry.id}
                className={`history-list-item ${selectedEntry?.id === entry.id ? 'selected' : ''}`}
                onClick={() => setSelectedEntry(entry)}
              >
                <div className="history-list-item-main">
                  <span className="history-list-count">{entry.totalCount || 0} colonies</span>
                  <span className={`history-list-model ${entry.modelType || ''}`}>
                    {(entry.modelType || 'N/A').toUpperCase()}
                  </span>
                </div>
                <div className="history-list-item-meta">
                  <span>{formatDate(entry.timestamp)}</span>
                </div>
                <div className="history-list-item-file">
                  <svg style={{ width: 12, height: 12, marginRight: 4, opacity: 0.6 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                    <circle cx="8.5" cy="8.5" r="1.5"></circle>
                    <polyline points="21 15 16 10 5 21"></polyline>
                  </svg>
                  {entry.imageName || 'Unknown file'}
                </div>
                <button 
                  className="history-delete-btn"
                  onClick={(e) => deleteEntry(entry.id, e)}
                  title="Delete this entry"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Detail View */}
        <div className="history-detail-container">
          {selectedEntry ? (
            <div className="history-detail">
              <div className="history-detail-header">
                <div>
                    <h2>Analysis Details</h2>
                    <span className="history-detail-date">{formatDate(selectedEntry.timestamp)}</span>
                </div>
                <button 
                  className="btn btn-secondary btn-sm"
                  onClick={() => window.open(`/api/reports/${selectedEntry.id}/pdf`, '_blank')}
                  title="Download PDF Report"
                >
                  <svg style={{ width: 14, height: 14, marginRight: 6 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                    <line x1="16" y1="13" x2="8" y2="13"></line>
                    <line x1="16" y1="17" x2="8" y2="17"></line>
                    <polyline points="10 9 9 9 8 9"></polyline>
                  </svg>
                  Download Report
                </button>
              </div>
              
              <div className="history-detail-section">
                <h3>Results Summary</h3>
                <div className="history-detail-grid">
                  <div className="history-detail-stat primary">
                    <span className="stat-value">{selectedEntry.totalCount || 0}</span>
                    <span className="stat-label">Total Colonies</span>
                  </div>
                  <div className="history-detail-stat">
                    <span className="stat-value">{(selectedEntry.modelType || 'N/A').toUpperCase()}</span>
                    <span className="stat-label">Detection Model</span>
                  </div>
                  <div className="history-detail-stat">
                    <span className="stat-value">{selectedEntry.confidenceThreshold ? `${(selectedEntry.confidenceThreshold * 100).toFixed(0)}%` : '40%'}</span>
                    <span className="stat-label">Confidence Threshold</span>
                  </div>
                </div>
              </div>

              {selectedEntry.classCounts && (
                <div className="history-detail-section">
                  <h3>Classification Breakdown</h3>
                  <div className="class-breakdown">
                    {/* Handle both array format [{name, count}] and object format {className: count} */}
                    {Array.isArray(selectedEntry.classCounts) ? (
                      // Array format from backend
                      selectedEntry.classCounts
                        .sort((a, b) => (b.count || 0) - (a.count || 0))
                        .map((item, index) => (
                          <div key={item.name || index} className="class-breakdown-item">
                            <div className="class-info">
                              <span className={`class-dot ${(item.name || '').toLowerCase().replace(/\./g, '-')}`}></span>
                              <span className="class-name">{item.name || 'Unknown'}</span>
                            </div>
                            <div className="class-stats">
                              <span className="class-count">{item.count || 0}</span>
                              <span className="class-percent">
                                {selectedEntry.totalCount ? (((item.count || 0) / selectedEntry.totalCount) * 100).toFixed(1) : 0}%
                              </span>
                            </div>
                          </div>
                        ))
                    ) : (
                      // Object format {className: count}
                      Object.entries(selectedEntry.classCounts)
                        .filter(([, count]) => typeof count === 'number')
                        .sort((a, b) => b[1] - a[1])
                        .map(([className, count]) => (
                          <div key={className} className="class-breakdown-item">
                            <div className="class-info">
                              <span className={`class-dot ${className.toLowerCase().replace(/\./g, '-')}`}></span>
                              <span className="class-name">{className}</span>
                            </div>
                            <div className="class-stats">
                              <span className="class-count">{count}</span>
                              <span className="class-percent">
                                {selectedEntry.totalCount ? ((count / selectedEntry.totalCount) * 100).toFixed(1) : 0}%
                              </span>
                            </div>
                          </div>
                        ))
                    )}
                  </div>
                </div>
              )}

              <div className="history-images-grid">
                {selectedEntry.thumbnail && (
                  <div className="history-detail-section">
                    <h3>Original Image</h3>
                    <div className="history-image-wrapper" onClick={() => handleImageClick(selectedEntry.thumbnail)}>
                      <img 
                        src={selectedEntry.thumbnail} 
                        alt="Original petri dish" 
                        className="history-detail-image"
                      />
                      <div className="image-zoom-hint">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <circle cx="11" cy="11" r="8"></circle>
                          <path d="m21 21-4.35-4.35"></path>
                          <path d="M11 8v6M8 11h6"></path>
                        </svg>
                      </div>
                    </div>
                  </div>
                )}

                {selectedEntry.annotatedImage && (
                  <div className="history-detail-section">
                    <h3>Detection Result</h3>
                    <div 
                      className="history-image-wrapper"
                      onClick={() => handleImageClick(formatImageSrc(selectedEntry.annotatedImage))}
                    >
                      <img 
                        src={formatImageSrc(selectedEntry.annotatedImage)} 
                        alt="YOLO Detection Result" 
                        className="history-detail-image"
                      />
                      <div className="image-zoom-hint">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <circle cx="11" cy="11" r="8"></circle>
                          <path d="m21 21-4.35-4.35"></path>
                          <path d="M11 8v6M8 11h6"></path>
                        </svg>
                      </div>
                    </div>
                  </div>
                )}

                {selectedEntry.heatmapImage && (
                  <div className="history-detail-section">
                    <h3>Density Heatmap</h3>
                    <div 
                      className="history-image-wrapper"
                      onClick={() => handleImageClick(formatImageSrc(selectedEntry.heatmapImage))}
                    >
                      <img 
                        src={formatImageSrc(selectedEntry.heatmapImage)} 
                        alt="Density Heatmap" 
                        className="history-detail-image"
                      />
                      <div className="image-zoom-hint">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <circle cx="11" cy="11" r="8"></circle>
                          <path d="m21 21-4.35-4.35"></path>
                          <path d="M11 8v6M8 11h6"></path>
                        </svg>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <div className="history-detail-section">
                <h3>File Information</h3>
                <div className="history-metadata">
                  <div className="metadata-item">
                    <span className="metadata-label">File Name</span>
                    <span className="metadata-value">{selectedEntry.imageName || 'Unknown'}</span>
                  </div>
                  <div className="metadata-item">
                    <span className="metadata-label">Analysis Date</span>
                    <span className="metadata-value">{formatDate(selectedEntry.timestamp)}</span>
                  </div>
                  <div className="metadata-item">
                    <span className="metadata-label">Analysis ID</span>
                    <span className="metadata-value" style={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                      #{selectedEntry.id}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="history-detail-empty">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" style={{ width: 48, height: 48, opacity: 0.5 }}>
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
              </svg>
              <p>Select an entry to view details</p>
            </div>
          )}
        </div>
      </div>

      {/* Image Zoom Modal */}
      {imageZoom && zoomImage && (
        <div className="image-zoom-modal" onClick={() => setImageZoom(false)}>
          <button className="zoom-close-btn" onClick={() => setImageZoom(false)}>×</button>
          <img src={zoomImage} alt="Zoomed view" className="zoomed-image" />
        </div>
      )}
    </div>
  );
}

export default History;
