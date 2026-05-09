import React, { useEffect } from 'react';
import { View, Text, StyleSheet, Image, ScrollView, TouchableOpacity, Platform } from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useTheme } from '../context/ThemeContext';

// Platform-specific shadow styles - defined before component to avoid hoisting issues
const shadowStyle = Platform.select({
  web: { boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08)' },
  default: { elevation: 4, shadowColor: '#000', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.08, shadowRadius: 12 }
});

export default function ResultScreen() {
    const route = useRoute();
    const navigation = useNavigation();
    const { theme } = useTheme();
    const colors = theme.colors;
    const { result } = route.params || {};

    // Helper to format base64
    const getImageSrc = (b64) => {
        if (!b64) return null;
        if (b64.startsWith('data:image')) return b64;
        return `data:image/jpeg;base64,${b64}`;
    };

    // Save history on mount
    useEffect(() => {
        if (result) {
            saveToHistory();
        }
    }, [result]);

    const saveToHistory = async () => {
        try {
             const newItem = {
                 id: Date.now().toString(),
                 date: new Date().toISOString(),
                 count: result.total_count,
                 thumbnail: getImageSrc(result.annotated_image || result.processed_image),
                 // Save full details for restoration
                 total_count: result.total_count,
                 class_counts: result.class_counts,
                 annotated_image: result.annotated_image,
                 processed_image: result.processed_image
             };
             
             const existing = await AsyncStorage.getItem('scan_history');
             const history = existing ? JSON.parse(existing) : [];
             history.push(newItem);
             
             // Limit to 20 items
             if (history.length > 20) history.shift();

             await AsyncStorage.setItem('scan_history', JSON.stringify(history));
        } catch (e) {
            console.error("Failed to save history", e);
        }
    }

    if (!result) {
        return (
            <View style={[styles.centerContainer, { backgroundColor: colors.background }]}>
                <Text style={styles.errorText}>No result data found.</Text>
                <TouchableOpacity style={[styles.homeButton, { backgroundColor: colors.text }]} onPress={() => navigation.popToTop()}>
                        <Text style={[styles.buttonText, { color: colors.background }]}>Go Home</Text>
                </TouchableOpacity>
            </View>
        );
    }

    const { total_count, annotated_image, class_counts, processed_image } = result;
    const displayImage = annotated_image || processed_image;

    return (
        <View style={[styles.container, { backgroundColor: colors.background }]}>
            <ScrollView contentContainerStyle={styles.scrollContent}>
                
                <View style={[styles.card, { backgroundColor: colors.card, borderColor: colors.border }, shadowStyle]}>
                    <Text style={[styles.header, { color: colors.text }]}>Analysis Results</Text>
                    
                    <View style={[styles.countContainer, { backgroundColor: theme.dark ? '#0C4A6E' : '#F0F9FF', borderColor: colors.secondary }]}>
                        <Text style={[styles.label, { color: theme.dark ? '#BAE6FD' : '#64748B' }]}>Total Colonies</Text>
                        <Text style={[styles.count, { color: colors.secondary }]}>{total_count}</Text>
                    </View>

                    {/* Class Counts Breakdown */}
                    {class_counts && class_counts.length > 0 && (
                        <View style={[styles.breakdownContainer, { backgroundColor: theme.dark ? '#3F3F46' : '#F4F4F5' }]}>
                            <Text style={[styles.subHeader, { color: colors.subtext }]}>Breakdown by Type</Text>
                            {class_counts.map((item, index) => (
                                <View key={index} style={styles.classRow}>
                                    <Text style={[styles.className, { color: colors.text }]}>{item.name}</Text>
                                    <View style={[styles.dots, { borderBottomColor: colors.border }]} />
                                    <Text style={[styles.classCount, { color: colors.text }]}>{item.count}</Text>
                                </View>
                            ))}
                        </View>
                    )}

                    {displayImage && (
                        <View style={styles.imageContainer}>
                            <Text style={[styles.imageLabel, { color: colors.text }]}>Annotated View</Text>
                            <Image 
                                source={{ uri: getImageSrc(displayImage) }} 
                                style={styles.image} 
                                resizeMode="contain" 
                            />
                        </View>
                    )}

                    <TouchableOpacity style={[styles.homeButton, { backgroundColor: colors.text }]} onPress={() => navigation.popToTop()}>
                        <Text style={[styles.buttonText, { color: colors.background }]}>Scan Another</Text>
                    </TouchableOpacity>
                </View>

            </ScrollView>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
    },
    centerContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
    },
    scrollContent: {
        flexGrow: 1,
        padding: 20,
        justifyContent: 'center',
    },
    card: {
        borderRadius: 16,
        padding: 24,
        alignItems: 'center',
        borderWidth: 1,
        width: '100%',
        maxWidth: 500,
        alignSelf: 'center',
    },
    header: {
        fontSize: 28,
        fontWeight: '800',
        marginBottom: 24,
    },
    countContainer: {
        alignItems: 'center',
        marginBottom: 24,
        paddingVertical: 20,
        paddingHorizontal: 40,
        borderRadius: 16,
        borderWidth: 1,
        width: '100%',
    },
    label: {
        fontSize: 14,
        marginBottom: 4,
        textTransform: 'uppercase',
        letterSpacing: 1.5,
        fontWeight: '700',
    },
    count: {
        fontSize: 56,
        fontWeight: '800',
    },
    breakdownContainer: {
        width: '100%',
        marginBottom: 24,
        padding: 16,
        borderRadius: 12,
    },
    subHeader: {
        fontSize: 16,
        fontWeight: '700',
        marginBottom: 12,
    },
    classRow: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 8,
    },
    className: {
        fontSize: 15,
        fontWeight: '500',
    },
    dots: {
        flex: 1,
        borderBottomWidth: 1,
        borderStyle: 'dotted',
        marginHorizontal: 8,
        marginBottom: 4,
    },
    classCount: {
        fontSize: 16,
        fontWeight: '700',
    },
    imageContainer: {
        width: '100%',
        marginBottom: 24,
        alignItems: 'center',
    },
    imageLabel: {
        fontSize: 16,
        fontWeight: '600',
        marginBottom: 12,
        alignSelf: 'flex-start',
    },
    image: {
        width: '100%',
        height: 300,
        borderRadius: 12,
        backgroundColor: '#F4F4F5',
    },
    homeButton: {
        paddingVertical: 16,
        paddingHorizontal: 32,
        borderRadius: 12,
        width: '100%',
        alignItems: 'center',
    },
    buttonText: {
        fontSize: 16,
        fontWeight: '600',
    },
    errorText: {
        fontSize: 18, 
        color: '#EF4444',
        marginBottom: 20
    }
});
