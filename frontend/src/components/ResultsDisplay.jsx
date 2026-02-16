import { useState } from 'react';
import { useNavigate } from 'react-router';
import FeedbackButton from './FeedbackButton';

function ResultsDisplay({ result, imageFile }) {
  const navigate = useNavigate();
  const [showAnnotated, setShowAnnotated] = useState(true);
  const [fullscreenImage, setFullscreenImage] = useState(null);

  const { total_count, class_counts, model_used, processed_image, annotated_image, detections, prediction_id } = result;
  
  // Calculate max count for bar scaling
  const maxCount = Math.max(...class_counts.map(c => c.count), 1);
  
  // Determine which image to show
  const displayImage = (showAnnotated && annotated_image) ? annotated_image : processed_image;
  const hasAnnotated = !!annotated_image;

  const openFullscreen = (imageSrc) => {
    setFullscreenImage(imageSrc);
  };

  const closeFullscreen = () => {
    setFullscreenImage(null);
  };

  // Navigate to correction page
  const handleCorrect = () => {
    navigate('/correct', {
      state: {
        imageUrl: imageFile ? URL.createObjectURL(imageFile) : (processed_image || annotated_image),
        detections: detections || [],
        predictionId: prediction_id,
        totalCount: total_count,
        imageName: imageFile?.name,
      },
    });
  };

  return (
    <div className="results-container">
      {/* Total Count */}
      <div className="count-display">
        <div className="count-number">{total_count}</div>
        <div className="count-label">
          Total Colonies Detected
          <span style={{ 
            marginLeft: 'var(--spacing-sm)', 
            padding: '2px 8px', 
            background: 'var(--bg-glass)', 
            borderRadius: 'var(--radius-full)',
            fontSize: '0.75rem'
          }}>
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
                <span className="class-name">{cls.name}</span>
                <div className="class-bar-container">
                  <div 
                    className="class-bar-fill"
                    style={{ width: `${Math.max((cls.count / maxCount) * 100, 10)}%` }}
                  />
                </div>
                <span className="class-count">{cls.count}</span>
              </div>
            ))}
        </div>
      )}

      {/* Image Display */}
      {displayImage && (
        <div>
          {hasAnnotated && (
            <div className="image-tabs">
              <button 
                className={`image-tab ${!showAnnotated ? 'active' : ''}`}
                onClick={() => setShowAnnotated(false)}
              >
                Original
              </button>
              <button 
                className={`image-tab ${showAnnotated ? 'active' : ''}`}
                onClick={() => setShowAnnotated(true)}
              >
                With Boxes
              </button>
            </div>
          )}
          
          <p style={{ 
            fontSize: '0.75rem', 
            color: 'var(--text-muted)', 
            marginBottom: 'var(--spacing-sm)',
            textAlign: 'center'
          }}>
            Click image to view fullscreen
          </p>
          
          <img 
            src={displayImage} 
            alt={showAnnotated ? "Annotated result" : "Processed image"} 
            className="result-image"
            onClick={() => openFullscreen(displayImage)}
          />
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

      {/* Correction Button */}
      {(annotated_image || processed_image) && detections && (
        <div className="correction-section">
          <button
            className="btn btn-primary"
            onClick={handleCorrect}
            style={{ marginBottom: 'var(--spacing-md)' }}
          >
            Review & Correct
          </button>
        </div>
      )}

      {/* Export Buttons */}
      <div className="export-section">
        <button
          className="export-btn"
          onClick={() => {
            import('../utils/export.js').then(({ exportToCSV }) => exportToCSV(result, imageFile?.name || 'Unknown'));
          }}
        >
          Export CSV
        </button>
        {(annotated_image || processed_image) && (
          <button
            className="export-btn"
            onClick={() => {
              import('../utils/export.js').then(({ downloadImage }) => {
                const imgToDownload = annotated_image || processed_image;
                const baseName = imageFile?.name?.replace(/\.[^/.]+$/, '') || 'colony_result';
                downloadImage(imgToDownload, `${baseName}_annotated.png`);
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
