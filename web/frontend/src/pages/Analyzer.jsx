import { useState, useCallback, useEffect } from "react";
import { Link } from "react-router-dom";
import ImageUpload from "../components/ImageUpload";
import ModelSelector from "../components/ModelSelector";
import ResultsDisplay from "../components/ResultsDisplay";
import Tutorial from "../components/Tutorial";
import { predictColonies } from "../services/api";

// Helper function to convert file to base64 for persistent storage
const fileToBase64 = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => resolve(reader.result);
    reader.onerror = (error) => reject(error);
  });
};

function Analyzer() {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null); // Keep for compatibility with render logic

  // Load settings from localStorage or defaults
  const [settings] = useState(() => {
    try {
      const saved = localStorage.getItem("userSettings");
      return saved ? JSON.parse(saved) : {};
    } catch (e) {
      return {};
    }
  });

  const [startTutorial, setStartTutorial] = useState(false);

  // Check for first-time visitor
  useEffect(() => {
    const seen = localStorage.getItem("tutorialSeen");
    if (!seen) {
      setTimeout(() => setStartTutorial(true), 1000); // Small delay for UI load
      localStorage.setItem("tutorialSeen", "true");
    }
  }, []);

  const [previewUrl, setPreviewUrl] = useState(null);
  const [modelType, setModelType] = useState(settings.defaultModel || "yolo");
  const [showBoxes, setShowBoxes] = useState(
    settings.showBoundingBoxes !== undefined
      ? settings.showBoundingBoxes
      : true,
  );
  const [confidenceThreshold, setConfidenceThreshold] = useState(
    settings.confidenceThreshold || 0.4,
  );
  const [loading, setLoading] = useState(false);
  const [loadingProgress, setLoadingProgress] = useState({
    current: 0,
    total: 0,
    elapsed: 0,
  });
  const [result, setResult] = useState(null);
  const [batchResults, setBatchResults] = useState([]);
  const [currentResultIndex, setCurrentResultIndex] = useState(0);
  const [error, setError] = useState(null);

  const [history, setHistory] = useState(() => {
    try {
      const saved = localStorage.getItem("analysisHistory");
      return saved ? JSON.parse(saved) : [];
    } catch (e) {
      return [];
    }
  });

  const handleFileSelect = useCallback((files) => {
    const fileList = Array.isArray(files) ? files : [files];
    setSelectedFiles(fileList);

    if (fileList.length > 0) {
      setSelectedFile(fileList[0]);
      setPreviewUrl(URL.createObjectURL(fileList[0]));
    } else {
      setSelectedFile(null);
      setPreviewUrl(null);
    }
    setResult(null);
    setBatchResults([]);
    setCurrentResultIndex(0);
    setError(null);
  }, []);

  const handleAnalyze = async () => {
    if (selectedFiles.length === 0) return;

    setLoading(true);
    setError(null);
    setResult(null);
    setBatchResults([]);
    setCurrentResultIndex(0);
    setLoadingProgress({ current: 0, total: selectedFiles.length, elapsed: 0 });

    // Start elapsed time counter
    const startTime = Date.now();
    const timerInterval = setInterval(() => {
      setLoadingProgress((prev) => ({
        ...prev,
        elapsed: Math.floor((Date.now() - startTime) / 1000),
      }));
    }, 1000);

    let successCount = 0;
    const newBatchResults = [];
    let lastError = null;

    try {
      for (let i = 0; i < selectedFiles.length; i++) {
        const file = selectedFiles[i];
        setLoadingProgress((prev) => ({ ...prev, current: i + 1 }));
        try {
          const data = await predictColonies(
            file,
            modelType,
            showBoxes,
            confidenceThreshold,
          );
          if (data.success) {
            successCount++;
            // Enhance data with file info for UI
            const resultWithMeta = {
              ...data,
              fileName: file.name,
              fileSize: file.size,
            };
            newBatchResults.push(resultWithMeta);
          } else {
            throw new Error(data.error || "Unknown server error");
          }
        } catch (err) {
          console.error(`Failed to analyze ${file.name}:`, err);
          lastError = err;
        }
      }

      clearInterval(timerInterval);

      if (successCount > 0) {
        setBatchResults(newBatchResults);
        setResult(newBatchResults[0]);
        setCurrentResultIndex(0);

        // Refresh history badge
        try {
          const saved = await import("../services/api").then((m) =>
            m.getHistory(),
          );
          setHistory(saved || []);
        } catch (e) {}

        if (selectedFiles.length > 1) {
          alert(
            `Batch complete: ${successCount}/${selectedFiles.length} images analyzed successfully.`,
          );
        }
      } else {
        setError(
          lastError ? lastError.message : "Analysis failed for all files",
        );
      }
    } catch (err) {
      setError(err.message || "Failed to connect to server");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setSelectedFiles([]);
    setSelectedFile(null);
    setPreviewUrl(null);
    setResult(null);
    setBatchResults([]);
    setCurrentResultIndex(0);
    setError(null);
  };

  const handleBatchNav = (direction) => {
    if (batchResults.length === 0) return;

    let newIndex = currentResultIndex + direction;
    if (newIndex < 0) newIndex = batchResults.length - 1;
    if (newIndex >= batchResults.length) newIndex = 0;

    setCurrentResultIndex(newIndex);
    setResult(batchResults[newIndex]);
    setSelectedFile(
      selectedFiles.find((f) => f.name === batchResults[newIndex].fileName) ||
        null,
    );
  };

  const downloadAnnotatedImage = () => {
    if (result?.annotated_image) {
      const link = document.createElement("a");
      link.href = `data:image/jpeg;base64,${result.annotated_image}`;
      link.download = `cfu-detection-${Date.now()}.jpg`;
      link.click();
    }
  };

  const exportResultsToCSV = () => {
    if (!result) return;

    const headers = ["Metric", "Value"];
    const rows = [
      ["Total Count", result.total_count],
      ["Model", modelType.toUpperCase()],
      ["Confidence Threshold", `${(confidenceThreshold * 100).toFixed(0)}%`],
      ["File Name", selectedFile?.name || "Unknown"],
      ["Date", new Date().toISOString()],
    ];

    if (result.class_counts) {
      Object.entries(result.class_counts).forEach(([cls, count]) => {
        rows.push([`Class: ${cls}`, count]);
      });
    }

    const csvContent = [headers, ...rows]
      .map((row) => row.join(","))
      .join("\n");
    const blob = new Blob([csvContent], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `cfu-analysis-${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="analyzer-page">
      <div className="analyzer-header">
        <div>
          <h1>Colony Analyzer</h1>
          <p>
            Upload a petri dish image to detect and classify bacterial colonies.
          </p>
        </div>
        <button
          className="btn btn-secondary btn-sm"
          onClick={() => setStartTutorial(true)}
          style={{ gap: 6 }}
        >
          <svg
            style={{ width: 16, height: 16 }}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <circle cx="12" cy="12" r="10" />
            <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
          Tutorial
        </button>
      </div>

      <Tutorial
        isActive={startTutorial}
        onComplete={() => setStartTutorial(false)}
      />

      <main className="main-grid">
        {/* Left Panel - Upload & Controls */}
        <div className="card">
          <h2 className="card-title">
            <svg
              className="icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="17 8 12 3 7 8"></polyline>
              <line x1="12" y1="3" x2="12" y2="15"></line>
            </svg>
            Upload Image
          </h2>

          <ImageUpload
            onFileSelect={handleFileSelect}
            previewUrl={previewUrl}
          />

          <div style={{ marginTop: "var(--spacing-lg)" }}>
            <ModelSelector modelType={modelType} onModelChange={setModelType} />
          </div>

          {modelType === "yolo" && (
            <div className="toggle-container">
              <div
                className={`toggle ${showBoxes ? "active" : ""}`}
                onClick={() => setShowBoxes(!showBoxes)}
              >
                <div className="toggle-knob" />
              </div>
              <span className="toggle-label">Show Bounding Boxes</span>
            </div>
          )}

          <div
            style={{
              marginTop: "var(--spacing-lg)",
              display: "flex",
              gap: "var(--spacing-md)",
            }}
          >
            <button
              className="btn btn-primary"
              onClick={handleAnalyze}
              disabled={!selectedFile || loading}
            >
              {loading ? (
                <>
                  <span
                    className="spinner"
                    style={{
                      width: 16,
                      height: 16,
                      borderTopColor: "inherit",
                      borderRightColor: "inherit",
                      borderBottomColor: "transparent",
                      borderLeftColor: "transparent",
                      marginRight: 8,
                      borderWidth: 2,
                    }}
                  />
                  {selectedFiles.length > 1
                    ? `Analyzing Batch...`
                    : "Analyzing..."}
                </>
              ) : (
                <>
                  <svg
                    style={{ width: 18, height: 18 }}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
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
            <div
              className="error-message"
              style={{ marginTop: "var(--spacing-md)" }}
            >
              {error}
            </div>
          )}
        </div>

        {/* Right Panel - Results */}
        <div className="card">
          <h2 className="card-title">
            <svg
              className="icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <line x1="16" y1="13" x2="8" y2="13"></line>
              <line x1="16" y1="17" x2="8" y2="17"></line>
              <polyline points="10 9 9 9 8 9"></polyline>
            </svg>
            Results
          </h2>

          {loading ? (
            <div className="loading-overlay">
              <div className="spinner" />
              <p className="loading-text">
                {loadingProgress.total > 1
                  ? `Processing image ${loadingProgress.current} of ${loadingProgress.total}...`
                  : "Analyzing image..."}
              </p>
              {/* Progress bar for batch */}
              {loadingProgress.total > 1 && (
                <div className="progress-bar-container">
                  <div
                    className="progress-bar-fill"
                    style={{
                      width: `${(loadingProgress.current / loadingProgress.total) * 100}%`,
                    }}
                  />
                </div>
              )}
              {/* Time info */}
              <div className="loading-stats">
                <span className="loading-time">
                  <svg
                    style={{ width: 14, height: 14 }}
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <circle cx="12" cy="12" r="10" />
                    <polyline points="12 6 12 12 16 14" />
                  </svg>
                  {loadingProgress.elapsed}s elapsed
                </span>

              </div>
            </div>
          ) : result ? (
            <>
              {batchResults.length > 1 && (
                <div className="batch-navigation">
                  <button
                    onClick={() => handleBatchNav(-1)}
                    className="nav-btn"
                  >
                    &lt; Prev
                  </button>
                  <span className="batch-status">
                    Result {currentResultIndex + 1} of {batchResults.length}
                    <div className="batch-filename">{result.fileName}</div>
                  </span>
                  <button onClick={() => handleBatchNav(1)} className="nav-btn">
                    Next &gt;
                  </button>
                </div>
              )}
              <ResultsDisplay
                result={result}
                imageFile={selectedFile}
                // Visual Settings
                boxColor={settings.boxColor}
                boxOpacity={settings.boxOpacity}
                // Report Settings
                labName={settings.labName}
                researcherName={settings.researcherName}
              />
            </>
          ) : (
            <div className="empty-state">
              <svg
                className="empty-state-icon"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                <circle cx="8.5" cy="8.5" r="1.5"></circle>
                <polyline points="21 15 16 10 5 21"></polyline>
              </svg>
              <p>Upload an image and click Analyze to see results</p>
            </div>
          )}
        </div>
      </main>

      {/* History Link Button */}
      <div className="analyzer-footer">
        <Link to="/history" className="action-btn action-btn-large">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <circle cx="12" cy="12" r="10"></circle>
            <polyline points="12 6 12 12 16 14"></polyline>
          </svg>
          View Analysis History
          {history.length > 0 && (
            <span className="history-badge">{history.length}</span>
          )}
        </Link>
      </div>
    </div>
  );
}

export default Analyzer;
