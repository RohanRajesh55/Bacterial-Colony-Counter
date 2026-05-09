import React from 'react';
import { View, Text, StyleSheet, ScrollView, Platform } from 'react-native';
import { useTheme } from '../context/ThemeContext';

// Platform-specific shadow styles - defined before component to avoid hoisting issues
const shadowStyle = Platform.select({
  web: { boxShadow: '0 4px 12px rgba(0,0,0,0.08)' },
  default: { elevation: 3, shadowColor: '#000', shadowOffset: {height: 4}, shadowOpacity: 0.1, shadowRadius: 4 }
});

export default function AboutScreen() {
  const { theme } = useTheme();
  const colors = theme.colors;

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={[styles.card, { backgroundColor: colors.card, borderColor: colors.border }, shadowStyle]}>
          <Text style={[styles.title, { color: colors.text }]}>About CFD</Text>
          <Text style={[styles.text, { color: colors.subtext }]}>
            The Bacterial Colony Counter (CFD) is an AI-powered tool designed to automate the process of counting bacterial colonies on petri dishes.
          </Text>

          <Text style={[styles.sectionTitle, { color: colors.primary }]}>How it works</Text>
          <Text style={[styles.text, { color: colors.subtext }]}>
            1. <Text style={[styles.bold, { color: colors.text }]}>Upload Scan:</Text> Take a photo or upload an image of your petri dish.
          </Text>
          <Text style={[styles.text, { color: colors.subtext }]}>
            2. <Text style={[styles.bold, { color: colors.text }]}>AI Analysis:</Text> Our deep learning models (CNN & YOLO) detect and count colonies instantly.
          </Text>
          <Text style={[styles.text, { color: colors.subtext }]}>
            3. <Text style={[styles.bold, { color: colors.text }]}>Results:</Text> Get an accurate count and a visualized map of detection.
          </Text>

          <Text style={[styles.sectionTitle, { color: colors.primary }]}>Technology</Text>
          <Text style={[styles.text, { color: colors.subtext }]}>
            Built with React Native, FastAPI, PyTorch, and OpenCV.
          </Text>
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    padding: 20,
    paddingBottom: 40,
  },
  card: {
    borderRadius: 12,
    padding: 24,
    borderWidth: 1,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    marginTop: 20,
    marginBottom: 8,
  },
  text: {
    fontSize: 16,
    lineHeight: 24,
    marginBottom: 8,
  },
  bold: {
    fontWeight: '700',
  }
});
