// Hardcoded backend URL for confirmed connectivity
const API_BASE = "http://localhost:8000/api";

/**
 * Predict colonies in an uploaded image
 * @param {File} imageFile - The image file to analyze
 * @param {string} modelType - 'cnn' or 'yolo'
 * @param {boolean} showBoxes - Whether to draw bounding boxes (YOLO only)
 * @param {number} confidenceThreshold - Confidence threshold for YOLO (0.1-0.9)
 * @returns {Promise<Object>} Prediction result
 */
export async function predictColonies(
  imageFile,
  modelType = "yolo",
  showBoxes = true,
  confidenceThreshold = 0.4,
) {
  const formData = new FormData();
  formData.append("image", imageFile);
  formData.append("model_type", modelType);
  formData.append("show_boxes", showBoxes.toString());
  formData.append("confidence_threshold", confidenceThreshold.toString());

  const response = await fetch(`${API_BASE}/predict`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP error ${response.status}`);
  }

  return response.json();
}

/**
 * Check API health
 * @returns {Promise<Object>} Health status
 */
export async function checkHealth() {
  const response = await fetch(`${API_BASE.replace("/api", "")}/health`);
  return response.json();
}

/**
 * Get analysis history
 * @returns {Promise<Array>} List of analyses
 */
export async function getHistory() {
  const response = await fetch(`${API_BASE}/history/`);
  if (!response.ok) {
    throw new Error("Failed to fetch history");
  }
  return response.json();
}

/**
 * Delete analysis record
 * @param {number} id - Analysis ID
 */
export async function deleteHistory(id) {
  const response = await fetch(`${API_BASE}/history/${id}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error("Failed to delete history");
  }
  return response.json();
}
