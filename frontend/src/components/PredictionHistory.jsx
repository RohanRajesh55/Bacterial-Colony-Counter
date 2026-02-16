import { useState, useEffect } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

function PredictionHistory() {
  const [predictions, setPredictions] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchHistory = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await fetch(
          `${API_BASE_URL}/api/history?page=${page}&size=10`,
          { credentials: 'include' }
        );

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to fetch history');
        }

        const data = await response.json();
        setPredictions(data.items);
        setTotalPages(data.pages);
      } catch (err) {
        setError(err.message || 'Failed to load history');
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, [page]);

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="loading-overlay">
        <div className="spinner" />
        <p className="loading-text">Loading history...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-message">
        {error}
      </div>
    );
  }

  if (predictions.length === 0) {
    return (
      <div className="empty-state">
        <svg className="empty-state-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
        <p>No analysis history yet</p>
        <p style={{ fontSize: '0.875rem', marginTop: 'var(--spacing-sm)' }}>
          Analyze some images to see your history here.
        </p>
      </div>
    );
  }

  return (
    <div className="history-container">
      <div className="history-grid">
        {predictions.map((prediction) => (
          <div key={prediction.id} className="history-card">
            <div className="history-card-image">
              {prediction.original_image_url ? (
                <img
                  src={prediction.original_image_url}
                  alt="Analysis"
                  className="history-thumbnail"
                />
              ) : (
                <div className="history-thumbnail-placeholder">
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" style={{ width: 32, height: 32, color: 'var(--text-muted)' }}>
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                      d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                </div>
              )}
            </div>
            <div className="history-card-content">
              <div className="history-card-count">{prediction.total_count}</div>
              <div className="history-card-label">colonies</div>
              <div className="history-card-date">
                {formatDate(prediction.created_at)}
              </div>
            </div>
          </div>
        ))}
      </div>

      {totalPages > 1 && (
        <div className="pagination">
          <button
            className="pagination-btn"
            onClick={() => setPage(page - 1)}
            disabled={page === 1}
          >
            Previous
          </button>
          <span className="pagination-info">
            Page {page} of {totalPages}
          </span>
          <button
            className="pagination-btn"
            onClick={() => setPage(page + 1)}
            disabled={page === totalPages}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}

export default PredictionHistory;
