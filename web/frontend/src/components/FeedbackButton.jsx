import { useState } from 'react';

const API_BASE = import.meta.env.DEV ? 'http://localhost:8000/api' : '/api';

function FeedbackButton({ result, imageFile }) {
  const [showModal, setShowModal] = useState(false);
  const [feedbackType, setFeedbackType] = useState('count');
  const [correctCount, setCorrectCount] = useState('');
  const [correctClass, setCorrectClass] = useState('');
  const [notes, setNotes] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const classNames = [
    'B.subtilis',
    'C.albicans',
    'Contamination',
    'Defect',
    'E.coli',
    'P.aeruginosa',
    'S.aureus'
  ];

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    
    try {
      // Create FormData to send image + feedback
      const formData = new FormData();
      
      // Add the original image
      if (imageFile) {
        formData.append('image', imageFile);
      }
      
      // Add feedback data
      formData.append('feedback_type', feedbackType);
      formData.append('original_count', result.total_count.toString());
      formData.append('original_model', result.model_used);
      formData.append('original_classes', JSON.stringify(result.class_counts));
      
      if (correctCount) {
        formData.append('correct_count', correctCount);
      }
      if (correctClass) {
        formData.append('correct_class', correctClass);
      }
      formData.append('notes', notes);
      
      // Send to backend
      const response = await fetch(`${API_BASE}/feedback`, {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to submit feedback');
      }
      
      const data = await response.json();
      console.log('Feedback saved:', data);
      
      setSubmitted(true);
      setTimeout(() => {
        setShowModal(false);
        setSubmitted(false);
        setFeedbackType('count');
        setCorrectCount('');
        setCorrectClass('');
        setNotes('');
      }, 2000);
      
    } catch (err) {
      console.error('Feedback error:', err);
      setError(err.message || 'Failed to submit feedback');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <div className="feedback-section">
        <button className="feedback-btn" onClick={() => setShowModal(true)}>
          Report Incorrect Result
        </button>
        <span style={{ 
          marginLeft: 'var(--spacing-sm)', 
          fontSize: '0.75rem', 
          color: 'var(--text-muted)' 
        }}>
          Help improve the model
        </span>
      </div>

      {showModal && (
        <div className="feedback-modal" onClick={() => setShowModal(false)}>
          <div className="feedback-form" onClick={(e) => e.stopPropagation()}>
            {submitted ? (
              <div className="feedback-success">
                <p style={{ fontSize: '2rem', marginBottom: 'var(--spacing-sm)' }}>✓</p>
                <p>Thank you for your feedback!</p>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 'var(--spacing-sm)' }}>
                  Image saved for model retraining
                </p>
              </div>
            ) : (
              <form onSubmit={handleSubmit}>
                <h3>Report Incorrect Result</h3>
                
                {error && (
                  <div style={{ 
                    padding: 'var(--spacing-sm)', 
                    background: '#fef2f2', 
                    border: '1px solid #ef4444',
                    borderRadius: 'var(--radius-sm)',
                    color: '#ef4444',
                    marginBottom: 'var(--spacing-md)',
                    fontSize: '0.875rem'
                  }}>
                    {error}
                  </div>
                )}
                
                <label>What was incorrect?</label>
                <select 
                  value={feedbackType} 
                  onChange={(e) => setFeedbackType(e.target.value)}
                >
                  <option value="count">Colony count is wrong</option>
                  <option value="classification">Classification is wrong</option>
                  <option value="both">Both count and classification</option>
                  <option value="other">Other issue</option>
                </select>

                {(feedbackType === 'count' || feedbackType === 'both') && (
                  <>
                    <label>
                      Correct colony count (Model predicted: {result.total_count})
                    </label>
                    <input
                      type="number"
                      min="0"
                      value={correctCount}
                      onChange={(e) => setCorrectCount(e.target.value)}
                      placeholder="Enter the correct count"
                    />
                  </>
                )}

                {(feedbackType === 'classification' || feedbackType === 'both') && (
                  <>
                    <label>Correct primary classification</label>
                    <select 
                      value={correctClass}
                      onChange={(e) => setCorrectClass(e.target.value)}
                    >
                      <option value="">Select correct class...</option>
                      {classNames.map(name => (
                        <option key={name} value={name}>{name}</option>
                      ))}
                    </select>
                  </>
                )}

                <label>Additional notes (optional)</label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Any additional details about what was wrong..."
                />

                <div className="feedback-actions">
                  <button 
                    type="button" 
                    className="feedback-cancel"
                    onClick={() => setShowModal(false)}
                    disabled={submitting}
                  >
                    Cancel
                  </button>
                  <button 
                    type="submit" 
                    className="feedback-submit"
                    disabled={submitting}
                  >
                    {submitting ? 'Saving...' : 'Submit Feedback'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </>
  );
}

export default FeedbackButton;
