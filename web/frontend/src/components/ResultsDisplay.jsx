import { useState } from "react";
import FeedbackButton from "./FeedbackButton";

// Helper function to ensure base64 images have proper data URI prefix
const formatBase64Image = (base64String) => {
  if (!base64String) return null;
  // If already has data URI prefix, return as-is
  if (base64String.startsWith("data:image")) {
    return base64String;
  }
  // Add prefix for JPEG (most common format from backend)
  return `data:image/jpeg;base64,${base64String}`;
};

// Class-specific colors matching the CSS class distribution colors
const CLASS_COLORS = {
  "B.subtilis": "#0ea5e9",    // Sky 500
  "C.albicans": "#22c55e",    // Green 500
  "Contamination": "#ef4444", // Red 500
  "Defect": "#71717a",        // Zinc 500
  "E.coli": "#06b6d4",        // Cyan 500
  "P.aeruginosa": "#8b5cf6",  // Violet 500
  "S.aureus": "#f97316",      // Orange 500
};

// Get color for a class (with fallback)
const getClassColor = (className) => {
  return CLASS_COLORS[className] || "#00FF00"; // Default green if class not found
};

function ResultsDisplay({
  result,
  imageFile,
  boxColor,
  boxOpacity,
  labName,
  researcherName,
}) {
  const [viewMode, setViewMode] = useState("annotated"); // 'original', 'annotated', 'heatmap'

  const [fullscreenImage, setFullscreenImage] = useState(null);

  const {
    total_count,
    class_counts,
    model_used,
    processed_image,
    annotated_image,
    heatmap_image,
  } = result;

  // Debug logging
  console.log("ResultsDisplay Result:", result);
  console.log("ResultsDisplay Settings:", {
    boxColor,
    boxOpacity,
    labName,
    researcherName,
  });
  if (result.detections) {
    console.log("Detections found:", result.detections.length);
    if (result.detections.length > 0) {
      console.log("Sample detection:", result.detections[0]);
    }
  } else {
    console.log("No detections in result");
  }

  // Calculate max count for bar scaling
  const maxCount = Math.max(...class_counts.map((c) => c.count), 1);

  // Determine which image to show (with proper base64 formatting)
  const formattedAnnotated = formatBase64Image(annotated_image);
  const formattedProcessed = formatBase64Image(processed_image);
  const formattedHeatmap = formatBase64Image(heatmap_image);

  let displayImage = formattedProcessed;
  const hasDetections = result.detections && result.detections.length > 0;

  if (viewMode === "annotated") {
    // Use annotated image with boxes when available, otherwise use processed image with client-side boxes
    if (formattedAnnotated) {
      displayImage = formattedAnnotated;
    } else if (hasDetections) {
      // Fallback: use processed image with client-side overlay boxes
      displayImage = formattedProcessed;
    }
  } else if (viewMode === "heatmap" && formattedHeatmap) {
    displayImage = formattedHeatmap;
  }

  const hasAnnotated = !!annotated_image;
  const hasHeatmap = !!heatmap_image;

  const openFullscreen = (imageSrc) => {
    setFullscreenImage(imageSrc);
  };

  const closeFullscreen = () => {
    setFullscreenImage(null);
  };

  return (
    <div className="results-container responsive-results">
      {/* Total Count */}
      <div className="count-display">
        <div className="count-number">{total_count}</div>
        <div className="count-label">
          Total Colonies Detected
          <span
            style={{
              marginLeft: "var(--spacing-sm)",
              padding: "2px 8px",
              background: "var(--bg-glass)",
              borderRadius: "var(--radius-full)",
              fontSize: "0.75rem",
            }}
          >
            {model_used.toUpperCase()}
          </span>
        </div>
      </div>

      {/* Class Distribution */}
      {class_counts.length > 0 && (
        <div className="class-distribution">
          <h3>Class Distribution</h3>
          {class_counts
            .sort((a, b) => b.count - a.count)
            .map((cls) => (
              <div key={cls.name} className="class-bar" data-class={cls.name}>
                <span className="class-name" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{
                    width: '12px',
                    height: '12px',
                    borderRadius: '50%',
                    backgroundColor: getClassColor(cls.name),
                    flexShrink: 0
                  }} />
                  {cls.name}
                </span>
                <div className="class-bar-container">
                  <div
                    className="class-bar-fill"
                    style={{
                      width: `${Math.max((cls.count / maxCount) * 100, 10)}%`,
                      backgroundColor: getClassColor(cls.name),
                    }}
                  />
                </div>
                <span className="class-count">{cls.count}</span>
              </div>
            ))}
        </div>
      )}

      {/* Image Display */}
      {displayImage && (
        <div style={{ position: "relative", display: "inline-block" }}>
          {(hasAnnotated || hasHeatmap || result.detections) && (
            <div className="image-tabs">
              <button
                className={`image-tab ${viewMode === "original" ? "active" : ""}`}
                onClick={() => setViewMode("original")}
              >
                Original
              </button>
              {(hasAnnotated || result.detections) && (
                <button
                  className={`image-tab ${viewMode === "annotated" ? "active" : ""}`}
                  onClick={() => setViewMode("annotated")}
                >
                  With Boxes
                </button>
              )}
              {hasHeatmap && (
                <button
                  className={`image-tab ${viewMode === "heatmap" ? "active" : ""}`}
                  onClick={() => setViewMode("heatmap")}
                >
                  Heatmap
                </button>
              )}
            </div>
          )}

          <p
            style={{
              fontSize: "0.75rem",
              color: "var(--text-muted)",
              marginBottom: "var(--spacing-sm)",
              textAlign: "center",
            }}
          >
            Click image to view fullscreen
          </p>

          <div style={{ position: "relative", width: "100%" }}>
            <img
              src={displayImage}
              alt="Analysis result"
              className="result-image"
              style={{ display: "block", width: "100%", height: "auto" }}
              onClick={() => openFullscreen(displayImage)}
            />

            {/* Client-side Bounding Box Rendering */}
            {viewMode === "annotated" && hasDetections && (
              <>
                {result.detections.map((det, idx) => (
                  <div
                    key={idx}
                    title={`${det.label} (${(det.confidence * 100).toFixed(0)}%)`}
                    style={{
                      position: "absolute",
                      left: `${det.xn * 100}%`,
                      top: `${det.yn * 100}%`,
                      width: `${det.wn * 100}%`,
                      height: `${det.hn * 100}%`,
                      border: `2px solid ${getClassColor(det.label)}`,
                      opacity: boxOpacity !== undefined ? boxOpacity : 0.8,
                      boxSizing: "border-box",
                      pointerEvents: "none",
                      zIndex: 10, // Ensure it sits on top
                    }}
                  />
                ))}
              </>
            )}
          </div>
        </div>
      )}

      {/* Fullscreen Modal */}
      {fullscreenImage && (
        <div className="image-modal" onClick={closeFullscreen}>
          <button className="image-modal-close" onClick={closeFullscreen}>
            ×
          </button>
          <img
            src={fullscreenImage}
            alt="Fullscreen view"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}

      {/* Export Buttons */}
      <div className="export-section">
        <button
          className="export-btn"
          onClick={() => {
            import("../utils/export.js").then(({ exportToCSV }) =>
              exportToCSV(result),
            );
          }}
        >
          Export CSV
        </button>
        <button
          className="export-btn"
          onClick={() => {
            import("../utils/export.js").then(({ downloadPDF }) => {
              downloadPDF(result.analysis_id, labName, researcherName);
            });
          }}
        >
          Download PDF Report
        </button>
        {(formattedAnnotated || formattedProcessed) && (
          <button
            className="export-btn"
            onClick={() => {
              import("../utils/export.js").then(({ downloadImage }) => {
                const imgToDownload = formattedAnnotated || formattedProcessed;
                downloadImage(imgToDownload, `colony_result_${Date.now()}.png`);
              });
            }}
          >
            Download Image
          </button>
        )}
      </div>

      {/* Feedback Button */}
      <FeedbackButton result={result} imageFile={imageFile} />
    </div>
  );
}

export default ResultsDisplay;
