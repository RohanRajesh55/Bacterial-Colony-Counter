// Always use proxy to ensure cookies are included with requests
const API_BASE = '/api';

/**
 * Predict colonies in an uploaded image
 * @param {File} imageFile - The image file to analyze
 * @param {string} modelType - 'rtdetr' (default)
 * @param {boolean} showBoxes - Whether to draw bounding boxes (YOLO only)
 * @param {number} confidenceThreshold - Confidence threshold for YOLO (0.1-0.9)
 * @returns {Promise<Object>} Prediction result
 */
export async function predictColonies(imageFile, modelType = 'rtdetr', showBoxes = true, confidenceThreshold = 0.40) {
  const formData = new FormData();
  formData.append('image', imageFile);
  formData.append('model_type', modelType);
  formData.append('show_boxes', showBoxes.toString());
  formData.append('confidence_threshold', confidenceThreshold.toString());

  const response = await fetch(`${API_BASE}/predict`, {
    method: 'POST',
    body: formData,
    credentials: 'include',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP error ${response.status}`);
  }

  return response.json();
}

/**
 * Save correction actions for a prediction
 * @param {string} predictionId - The prediction ID
 * @param {Array} actions - Array of correction actions
 * @returns {Promise<Object>} Correction response with corrected count
 */
export async function saveCorrections(predictionId, actions) {
  const response = await fetch(`${API_BASE}/corrections`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      prediction_id: predictionId,
      actions: actions,
    }),
    credentials: 'include',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP error ${response.status}`);
  }

  return response.json();
}

/**
 * Get correction summary for a prediction
 * @param {string} predictionId - The prediction ID
 * @returns {Promise<Object>} Correction summary
 */
export async function getCorrections(predictionId) {
  const response = await fetch(`${API_BASE}/corrections/${predictionId}`, {
    method: 'GET',
    credentials: 'include',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP error ${response.status}`);
  }

  return response.json();
}

/**
 * Check API health
 * @returns {Promise<Object>} Health status
 */
export async function checkHealth() {
  const response = await fetch(`${API_BASE.replace('/api', '')}/health`);
  return response.json();
}
