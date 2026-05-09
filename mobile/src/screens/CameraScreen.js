import { CameraView, CameraType, useCameraPermissions } from 'expo-camera';
import { useState } from 'react';
import { Button, StyleSheet, Text, TouchableOpacity, View, Image, ActivityIndicator, Alert } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { uploadImage } from '../services/api';

export default function CameraScreen() {
  const [facing, setFacing] = useState('back');
  const [permission, requestPermission] = useCameraPermissions();
  const [cameraRef, setCameraRef] = useState(null);
  const [photo, setPhoto] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigation = useNavigation();

  if (!permission) {
    // Camera permissions are still loading.
    return <View />;
  }

  if (!permission.granted) {
    // Camera permissions are not granted yet.
    return (
      <View style={styles.container}>
        <Text style={styles.message}>We need your permission to show the camera</Text>
        <Button onPress={requestPermission} title="grant permission" />
      </View>
    );
  }

  function toggleCameraFacing() {
    setFacing(current => (current === 'back' ? 'front' : 'back'));
  }

  const takePicture = async () => {
      if (cameraRef) {
          const photo = await cameraRef.takePictureAsync({
              quality: 1,
              base64: false,
              exif: false,
              skipProcessing: true, // Faster capture
          });
          setPhoto(photo.uri);
      }
  };

  const retakePicture = () => {
      setPhoto(null);
  };

  const confirmPicture = async () => {
      if (!photo) return;
      setLoading(true);
      try {
          // Upload directly from Camera Screen for smoother UX
          console.log("Uploading from Camera:", photo);
          const data = await uploadImage(photo);
          console.log("Analysis success");
          // Navigate to Result, replacing Camera in stack so 'Back' goes to Home
          navigation.replace('Result', { result: data });
      } catch (error) {
          Alert.alert("Error", error.message);
          setLoading(false);
      }
  };

  if (photo) {
      return (
          <View style={styles.container}>
              <Image source={{ uri: photo }} style={styles.preview} />
              <View style={styles.controls}>
                  <TouchableOpacity style={styles.button} onPress={retakePicture}>
                      <Text style={styles.text}>Retake</Text>
                  </TouchableOpacity>
                  <TouchableOpacity style={[styles.button, styles.confirmBtn]} onPress={confirmPicture} disabled={loading}>
                      {loading ? <ActivityIndicator color="#fff"/> : <Text style={styles.text}>Analyze</Text>}
                  </TouchableOpacity>
              </View>
          </View>
      );
  }

  return (
    <View style={styles.container}>
      <CameraView style={styles.camera} facing={facing} ref={ref => setCameraRef(ref)}>
        <View style={styles.buttonContainer}>
          <TouchableOpacity style={styles.captureButton} onPress={takePicture}>
             <View style={styles.captureInner} />
          </TouchableOpacity>
          <TouchableOpacity style={styles.flipButton} onPress={toggleCameraFacing}>
            <Text style={styles.text}>Flip</Text>
          </TouchableOpacity>
        </View>
      </CameraView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    backgroundColor: '#000',
  },
  message: {
    textAlign: 'center',
    paddingBottom: 10,
    color: 'white',
  },
  camera: {
    flex: 1,
  },
  buttonContainer: {
    flex: 1,
    flexDirection: 'row',
    backgroundColor: 'transparent',
    marginBottom: 40,
    justifyContent: 'center',
    alignItems: 'flex-end',
  },
  captureButton: {
      width: 70,
      height: 70,
      borderRadius: 35,
      borderWidth: 5,
      borderColor: 'white',
      justifyContent: 'center',
      alignItems: 'center',
  },
  captureInner: {
      width: 58,
      height: 58,
      borderRadius: 29,
      backgroundColor: 'white',
  },
  flipButton: {
    position: 'absolute',
    right: 30,
    bottom: 20,
  },
  text: {
    fontSize: 18,
    fontWeight: 'bold',
    color: 'white',
  },
  preview: {
      flex: 1,
      resizeMode: 'contain',
  },
  controls: {
      flexDirection: 'row',
      justifyContent: 'space-around',
      padding: 20,
      backgroundColor: 'black',
  },
  button: {
      padding: 15,
      borderRadius: 8,
      backgroundColor: '#333',
      width: 100,
      alignItems: 'center',
  },
  confirmBtn: {
      backgroundColor: '#34C759',
  }
});
