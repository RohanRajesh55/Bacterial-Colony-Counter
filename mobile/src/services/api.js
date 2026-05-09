import axios from 'axios';
import { Platform } from 'react-native';

// REPLACE WITH YOUR COMPUTERS IP ADDRESS IF RUNNING ON PHYSICAL DEVICE
// Example: 'http://192.168.1.5:8000'
// 'http://10.0.2.2:8000' works for Android Emulator
// 'http://localhost:8000' works for Web
const BASE_URL = Platform.OS === 'web' 
  ? 'http://localhost:8000' 
  : 'http://10.0.2.2:8000'; 

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 10000,
});

export const checkServerConnection = async () => {
    try {
        const response = await api.get('/docs'); // Simple check
        return true;
    } catch (error) {
        console.error("Server connection failed:", error);
        return false;
    }
};

export const uploadImage = async (imageUri) => {
  const formData = new FormData();
  
  if (Platform.OS === 'web') {
      // Fetch the blob from the blob URL
      const response = await fetch(imageUri);
      const blob = await response.blob();
      formData.append('image', blob, 'upload.jpg');
  } else {
      // Native (Android/iOS)
      const filename = imageUri.split('/').pop();
      const match = /\.(\w+)$/.exec(filename);
      const type = match ? `image/${match[1]}` : 'image/jpeg';

      formData.append('image', {
        uri: Platform.OS === 'ios' ? imageUri.replace('file://', '') : imageUri,
        name: filename || 'upload.jpg',
        type,
      });
  }
  
  // Add other parameters if needed (e.g., confidence threshold)
  formData.append('confidence_threshold', '0.40');

  try {
    const response = await api.post('/api/predict', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  } catch (error) {
    if (error.response) {
      console.error("API Error Response:", error.response.data);
      throw new Error(error.response.data.detail || "Server error");
    } else if (error.request) {
        console.error("API No Response:", error.request);
        throw new Error("No response from server. Check connection.");
    } else {
        console.error("API Error:", error.message);
        throw new Error(error.message);
    }
  }
};

export default api;
