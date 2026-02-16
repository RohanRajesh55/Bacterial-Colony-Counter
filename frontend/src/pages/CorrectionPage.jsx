import { useRef, useState, useEffect, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router';
import CorrectionCanvas from '../components/CorrectionCanvas';
import CanvasToolbar from '../components/CanvasToolbar';
import MiniMap from '../components/MiniMap';
import ConfidencePanel from '../components/ConfidencePanel';
import { saveCorrections } from '../services/api';

/**
 * Full-page correction editor for fixing prediction results
 * Features: TNTC warning, confidence guidance, mini-map, export, save
 */
export default function CorrectionPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const canvasRef = useRef(null);

  // Get prediction data from route state
  const { imageUrl, detections, predictionId, totalCount, imageName } = location.state || {};

  const [activeTool, setActiveTool] = useState('select');
  const [showTntcBanner, setShowTntcBanner] = useState(true);
  const [showConfidence, setShowConfidence] = useState(false);
  const [showMiniMap, setShowMiniMap] = useState(false);
  const [exportFormat, setExportFormat] = useState('jpeg');
  const [saveStatus, setSaveStatus] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');

  // State-driven correction info (updated via onCorrectionChange callback)
  const [correctionInfo, setCorrectionInfo] = useState({
    colonyCount: totalCount || 0,
    correctionSummary: { added: 0, removed: 0, adjusted: 0, split: 0 },
    canUndo: false,
    canRedo: false,
  });

  // Redirect if no prediction data
  useEffect(() => {
    if (!imageUrl || !detections) {
      navigate('/');
    }
  }, [imageUrl, detections, navigate]);

  // TNTC warning logic
  const isTntc = totalCount > 300;

  // Unsaved changes guard — warn before losing corrections
  const hasUnsavedChanges = correctionInfo.correctionSummary.added > 0
    || correctionInfo.correctionSummary.removed > 0
    || correctionInfo.correctionSummary.adjusted > 0
    || correctionInfo.correctionSummary.split > 0;

  useEffect(() => {
    if (!hasUnsavedChanges) return;
    const handler = (e) => {
      e.preventDefault();
      e.returnValue = '';
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [hasUnsavedChanges]);

  // Callback from canvas when corrections change
  const handleCorrectionChange = useCallback((info) => {
    setCorrectionInfo({
      colonyCount: info.colonyCount,
      correctionSummary: info.correctionSummary,
      canUndo: info.canUndo,
      canRedo: info.canRedo,
    });
  }, []);

  // Handle save corrections
  const handleSave = async () => {
    if (!canvasRef.current || !predictionId) return;

    setSaveStatus('saving');
    setErrorMessage('');

    try {
      const { correctionState } = canvasRef.current;
      const actions = correctionState.undoStack || [];

      await saveCorrections(predictionId, actions);
      setSaveStatus('saved');

      setTimeout(() => setSaveStatus(null), 3000);
    } catch (error) {
      setSaveStatus('error');
      setErrorMessage(error.message || 'Failed to save corrections');
      setTimeout(() => setSaveStatus(null), 5000);
    }
  };

  // Handle export annotated image
  const handleExport = () => {
    if (!canvasRef.current || !imageUrl) return;

    const { correctionState } = canvasRef.current;
    const { activeDetections } = correctionState;

    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = img.width;
      canvas.height = img.height;
      const ctx = canvas.getContext('2d');

      ctx.drawImage(img, 0, 0);

      activeDetections.forEach((detection) => {
        const { box, source = 'model', confidence } = detection;
        if (!box || box.length < 4) return;

        const [x1, y1, x2, y2] = box;
        const width = x2 - x1;
        const height = y2 - y1;

        const strokeStyle = source === 'user' ? '#3b82f6' : '#22c55e';

        ctx.strokeStyle = strokeStyle;
        ctx.lineWidth = 2;
        ctx.strokeRect(x1, y1, width, height);

        if (source === 'model' && confidence != null) {
          const label = `${(confidence * 100).toFixed(1)}%`;
          ctx.font = '14px Inter, sans-serif';
          ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
          const metrics = ctx.measureText(label);
          ctx.fillRect(x1, y1 - 20, metrics.width + 8, 20);
          ctx.fillStyle = 'white';
          ctx.fillText(label, x1 + 4, y1 - 6);
        }
      });

      const mimeType = exportFormat === 'png' ? 'image/png' : 'image/jpeg';
      const quality = exportFormat === 'jpeg' ? 0.9 : undefined;

      canvas.toBlob(
        (blob) => {
          if (!blob) return;

          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          const baseName = (imageName || 'colony_result').replace(/\.[^/.]+$/, '');
          a.download = `${baseName}_corrected.${exportFormat}`;
          a.click();
          URL.revokeObjectURL(url);
        },
        mimeType,
        quality
      );
    };

    img.src = imageUrl;
  };

  const handleUndo = () => canvasRef.current?.undo();
  const handleRedo = () => canvasRef.current?.redo();

  if (!imageUrl || !detections) {
    return null;
  }

  return (
    <div className="correction-page">
      {/* TNTC Warning Banner */}
      {isTntc && showTntcBanner && (
        <div className="tntc-banner">
          <div className="tntc-banner-content">
            <span className="tntc-banner-icon">!</span>
            <span className="tntc-banner-text">
              <strong>TNTC - Too Numerous To Count.</strong> Approximate count: ~{totalCount}.
              Manual verification recommended for regulatory use.
            </span>
            <button
              className="tntc-banner-close"
              onClick={() => setShowTntcBanner(false)}
              aria-label="Dismiss warning"
            >
              x
            </button>
          </div>
        </div>
      )}

      {/* Toolbar */}
      <div className="correction-toolbar-container">
        <CanvasToolbar
          activeTool={activeTool}
          onToolChange={setActiveTool}
          colonyCount={correctionInfo.colonyCount}
          correctionSummary={correctionInfo.correctionSummary}
          onUndo={handleUndo}
          onRedo={handleRedo}
          canUndo={correctionInfo.canUndo}
          canRedo={correctionInfo.canRedo}
        />

        {/* Additional controls */}
        <div className="correction-toolbar-controls">
          <button
            className={`correction-toolbar-toggle ${showConfidence ? 'active' : ''}`}
            onClick={() => setShowConfidence(!showConfidence)}
            title="Highlight low-confidence detections"
          >
            Low Confidence
          </button>

          <button
            className={`correction-toolbar-toggle ${showMiniMap ? 'active' : ''}`}
            onClick={() => setShowMiniMap(!showMiniMap)}
            title="Show mini-map overview"
          >
            Mini-map
          </button>

          <select
            className="correction-toolbar-select"
            value={exportFormat}
            onChange={(e) => setExportFormat(e.target.value)}
            title="Export format"
          >
            <option value="jpeg">JPEG</option>
            <option value="png">PNG</option>
          </select>

          <button
            className="correction-toolbar-btn-primary"
            onClick={handleExport}
            title="Download corrected annotated image"
          >
            Download
          </button>

          <button
            className="correction-toolbar-btn-primary"
            onClick={handleSave}
            disabled={saveStatus === 'saving'}
            title="Save corrections to server"
          >
            {saveStatus === 'saving' ? 'Saving...' : 'Save'}
          </button>

          <button
            className="correction-toolbar-btn-secondary"
            onClick={() => {
              if (hasUnsavedChanges && !window.confirm('You have unsaved corrections. Leave anyway?')) return;
              navigate('/');
            }}
            title="Return to home"
          >
            Back
          </button>
        </div>
      </div>

      {/* Save status toast */}
      {saveStatus === 'saved' && (
        <div className="correction-toast correction-toast-success">
          Corrections saved successfully
        </div>
      )}
      {saveStatus === 'error' && (
        <div className="correction-toast correction-toast-error">
          {errorMessage || 'Failed to save corrections'}
        </div>
      )}

      {/* Main canvas area */}
      <div className="correction-canvas-wrapper">
        <CorrectionCanvas
          ref={canvasRef}
          imageUrl={imageUrl}
          initialDetections={detections}
          activeTool={activeTool}
          onCorrectionChange={handleCorrectionChange}
        />

        {showConfidence && (
          <ConfidencePanel
            detections={detections}
            canvasRef={canvasRef}
          />
        )}

        {showMiniMap && (
          <MiniMap
            imageUrl={imageUrl}
            detections={detections}
            canvasRef={canvasRef}
          />
        )}
      </div>
    </div>
  );
}
