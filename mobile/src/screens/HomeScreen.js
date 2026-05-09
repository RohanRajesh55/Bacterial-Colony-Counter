import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ActivityIndicator, Alert, Platform } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { useNavigation } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { uploadImage } from '../services/api';
import { useTheme } from '../context/ThemeContext';

// Platform-specific shadow styles - defined before component to avoid hoisting issues
const shadowStyle = Platform.select({
  web: { boxShadow: '0px 4px 12px rgba(0, 0, 0, 0.08)' },
  default: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.08,
    shadowRadius: 12,
    elevation: 4,
  }
});

export default function HomeScreen() {
  const navigation = useNavigation();
  const [loading, setLoading] = useState(false);
  const { theme } = useTheme();
  const colors = theme.colors;

  const pickImage = async () => {
    // Gallery
    let result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: false, 
      quality: 1,
    });

    if (!result.canceled) {
      handleImage(result.assets[0].uri);
    }
  };

  const handleImage = async (uri) => {
    console.log("Processing image:", uri);
    setLoading(true);
    try {
      const data = await uploadImage(uri);
      console.log("Upload success:", data);
      navigation.navigate('Result', { result: data });
    } catch (error) {
      Alert.alert("Error", error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <View style={styles.header}>
          <Text style={[styles.title, { color: colors.text }]}>Colony Counter</Text>
          <Text style={[styles.subtitle, { color: colors.subtext }]}>Automated Lab Analysis</Text>
      </View>
      
      <View style={[styles.card, { backgroundColor: colors.card, borderColor: colors.border }, shadowStyle]}>
        <View style={styles.buttonContainer}>
          <TouchableOpacity style={[styles.button, styles.primaryButton]} onPress={pickImage} disabled={loading}>
            <Ionicons name="images-outline" size={24} color="#FFFFFF" style={styles.buttonIcon} />
            <Text style={styles.buttonText}>Select from Gallery</Text>
          </TouchableOpacity>

          <TouchableOpacity style={[styles.button, styles.secondaryButton]} onPress={() => navigation.navigate('Camera')} disabled={loading}>
            <Ionicons name="camera-outline" size={24} color="#FFFFFF" style={styles.buttonIcon} />
            <Text style={styles.buttonText}>Open Camera</Text>
          </TouchableOpacity>
        </View>
      </View>

      {loading && (
        <View style={[styles.loadingOverlay, { backgroundColor: 'rgba(0,0,0,0.7)' }]}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={[styles.loadingText, { color: 'white' }]}>Analyzing Sample...</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  header: {
    marginBottom: 48,
    alignItems: 'center',
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    marginBottom: 8,
    textAlign: 'center',
    letterSpacing: -0.5,
  },
  subtitle: {
    fontSize: 16,
    opacity: 0.7,
    letterSpacing: 0.5,
    textTransform: 'uppercase',
    fontWeight: '500',
  },
  card: {
    width: '100%',
    maxWidth: 400,
    borderRadius: 20,
    padding: 32,
    borderWidth: 1,
  },
  buttonContainer: {
    gap: 16,
  },
  button: {
    paddingVertical: 16,
    paddingHorizontal: 24,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
    ...Platform.select({
      web: { cursor: 'pointer', transition: 'all 0.2s ease' },
    }),
  },
  primaryButton: {
    backgroundColor: '#2563EB', // Professional Blue
  },
  secondaryButton: {
    backgroundColor: '#0F172A', // Slate 900
  },
  buttonIcon: {
    marginRight: 12,
  },
  buttonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
    letterSpacing: 0.3,
  },
  loadingOverlay: {
    ...StyleSheet.absoluteFillObject,
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 100,
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    fontWeight: '500',
  }
});
