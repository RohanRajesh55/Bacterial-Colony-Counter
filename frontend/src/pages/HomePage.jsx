import { useState, useCallback } from 'react';
import ImageUpload from '../components/ImageUpload';
import ResultsDisplay from '../components/ResultsDisplay';
import { predictColonies } from '../services/api';

function HomePage() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [showBoxes, setShowBoxes] = useState(true);
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.40);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleFileSelect = useCallback((file) => {
    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setResult(null);
    setError(null);
  }, []);

  const handleAnalyze = async () => {
    if (!selectedFile) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await predictColonies(selectedFile, 'rtdetr', showBoxes, confidenceThreshold);
      setResult(data);
    } catch (err) {
      setError(err.message || 'Failed to connect to server');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setResult(null);
    setError(null);
  };

  return (
    <>
      <main className="main-grid">
        {/* Left Panel - Upload & Controls */}
        <div className="card">
          <h2 className="card-title">
            <svg className="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            Upload Image
          </h2>

          <ImageUpload
            onFileSelect={handleFileSelect}
            previewUrl={previewUrl}
          />

          <div className="toggle-container">
            <div
              className={`toggle ${showBoxes ? 'active' : ''}`}
              onClick={() => setShowBoxes(!showBoxes)}
            >
              <div className="toggle-knob" />
            </div>
            <span className="toggle-label">Show Bounding Boxes</span>
          </div>

          <div style={{ marginTop: 'var(--spacing-lg)', display: 'flex', gap: 'var(--spacing-md)' }}>
            <button
              className="btn btn-primary"
              onClick={handleAnalyze}
              disabled={!selectedFile || loading}
            >
              {loading ? (
                <>
                  <span className="spinner" style={{ width: 20, height: 20, borderWidth: 2 }} />
                  Analyzing...
                </>
              ) : (
                <>
                  <svg style={{ width: 20, height: 20 }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                  Analyze
                </>
              )}
            </button>

            {selectedFile && (
              <button className="btn btn-secondary" onClick={handleReset}>
                Clear
              </button>
            )}
          </div>

          {error && (
            <div className="error-message" style={{ marginTop: 'var(--spacing-md)' }}>
              {error}
            </div>
          )}
        </div>

        {/* Right Panel - Results */}
        <div className="card">
          <h2 className="card-title">
            <svg className="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            Results
          </h2>

          {loading ? (
            <div className="loading-overlay">
              <div className="spinner" />
              <p className="loading-text">Analyzing image...</p>
            </div>
          ) : result ? (
            <ResultsDisplay result={result} imageFile={selectedFile} />
          ) : (
            <div className="empty-state">
              <svg className="empty-state-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
              </svg>
              <p>Upload an image and click Analyze to see results</p>
            </div>
          )}
        </div>
      </main>

      <footer style={{ textAlign: 'center', marginTop: 'var(--spacing-2xl)', color: 'var(--text-muted)' }}>
        <p>Built with FastAPI + React | RT-DETR Model</p>
      </footer>
    </>
  );
}

export default HomePage;
