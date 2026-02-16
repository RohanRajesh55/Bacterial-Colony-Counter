import { useMemo } from 'react';

/**
 * Panel showing low-confidence detections for guided review
 * Highlights detections with confidence < 0.6
 */
export default function ConfidencePanel({ detections = [], canvasRef }) {
  // Filter and sort low-confidence detections
  const lowConfidenceDetections = useMemo(() => {
    return detections
      .filter((d) => d.confidence != null && d.confidence < 0.6 && d.status !== 'removed')
      .sort((a, b) => a.confidence - b.confidence); // Lowest first
  }, [detections]);

  // Handle click to zoom to detection
  const handleDetectionClick = (detection) => {
    if (!canvasRef?.current || !detection.box) return;

    const [x1, y1, x2, y2] = detection.box;
    const centerX = (x1 + x2) / 2;
    const centerY = (y1 + y2) / 2;

    // Zoom and pan main canvas to center on this detection
    // This requires exposing pan/zoom methods in CorrectionCanvas
    // For now, this is a placeholder
    console.log('Zoom to detection:', { centerX, centerY, confidence: detection.confidence });
  };

  if (lowConfidenceDetections.length === 0) {
    return (
      <div className="confidence-panel">
        <div className="confidence-panel-header">
          <h3>Low Confidence</h3>
          <span className="confidence-panel-badge">0</span>
        </div>
        <p className="confidence-panel-empty">
          No low-confidence detections found. All detections have confidence ≥ 60%.
        </p>
      </div>
    );
  }

  return (
    <div className="confidence-panel">
      <div className="confidence-panel-header">
        <h3>Low Confidence</h3>
        <span className="confidence-panel-badge">{lowConfidenceDetections.length}</span>
      </div>
      <p className="confidence-panel-subtitle">
        Review these detections for accuracy
      </p>

      <div className="confidence-panel-list">
        {lowConfidenceDetections.map((detection, index) => {
          const { id, confidence, box } = detection;
          const [x1, y1] = box || [0, 0];

          return (
            <div
              key={id || index}
              className="confidence-panel-item"
              onClick={() => handleDetectionClick(detection)}
            >
              <div className="confidence-panel-item-info">
                <span className="confidence-panel-item-label">
                  Detection #{index + 1}
                </span>
                <span className="confidence-panel-item-position">
                  ({Math.round(x1)}, {Math.round(y1)})
                </span>
              </div>
              <div className="confidence-panel-item-confidence">
                <div
                  className="confidence-panel-item-bar"
                  style={{ width: `${confidence * 100}%` }}
                />
                <span className="confidence-panel-item-value">
                  {(confidence * 100).toFixed(1)}%
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
