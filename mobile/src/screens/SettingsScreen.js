import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, Switch, TouchableOpacity, ScrollView, Platform } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../context/ThemeContext';

export default function SettingsScreen() {
    const { theme, isDark, toggleTheme } = useTheme();
    const colors = theme.colors;

    const [notifications, setNotifications] = useState(true);
    const [sensitivity, setSensitivity] = useState('Medium');

    const SettingItem = ({ icon, title, value, type, onPress }) => (
        <TouchableOpacity 
            style={[styles.item, { borderBottomColor: colors.border }]} 
            onPress={onPress} 
            disabled={type === 'switch'}
        >
            <View style={styles.itemLeft}>
                <View style={[styles.iconContainer, { backgroundColor: iconColor(title) }]}>
                    <Ionicons name={icon} size={20} color="white" />
                </View>
                <Text style={[styles.itemTitle, { color: colors.text }]}>{title}</Text>
            </View>
            <View style={styles.itemRight}>
                {type === 'switch' && (
                    <Switch 
                        value={value} 
                        onValueChange={onPress}
                        trackColor={{ true: colors.primary, false: colors.border }}
                        thumbColor={Platform.OS === 'android' ? '#f4f3f4' : ''}
                    />
                )}
                {type === 'select' && (
                    <View style={styles.selectContainer}>
                        <Text style={[styles.selectText, { color: colors.subtext }]}>{value}</Text>
                        <Ionicons name="chevron-forward" size={16} color={colors.subtext} />
                    </View>
                )}
                {type === 'link' && (
                    <Ionicons name="chevron-forward" size={16} color={colors.subtext} />
                )}
            </View>
        </TouchableOpacity>
    );

    const iconColor = (t) => {
        if (t.includes('Dark')) return isDark ? '#71717A' : '#18181B'; // Adaptive icon bg
        if (t.includes('Noti')) return colors.primary;
        if (t.includes('Sens')) return colors.secondary;
        return '#71717A';
    };

    return (
        <ScrollView style={[styles.container, { backgroundColor: colors.background }]}>
            <Text style={[styles.header, { color: colors.text }]}>Settings</Text>

            <View style={styles.section}>
                <Text style={styles.sectionHeader}>Preferences</Text>
                <View style={[styles.card, { backgroundColor: colors.card, borderColor: colors.border }]}>
                    <SettingItem 
                        icon="moon" 
                        title="Dark Mode" 
                        value={isDark} 
                        type="switch" 
                        onPress={toggleTheme} 
                    />
                    <SettingItem 
                        icon="notifications" 
                        title="Notifications" 
                        value={notifications} 
                        type="switch" 
                        onPress={(v) => setNotifications(v)} 
                    />
                </View>
            </View>

            <View style={styles.section}>
                <Text style={styles.sectionHeader}>Analysis</Text>
                <View style={[styles.card, { backgroundColor: colors.card, borderColor: colors.border }]}>
                    <SettingItem 
                        icon="pulse" 
                        title="Model Sensitivity" 
                        value={sensitivity} 
                        type="select" 
                        onPress={() => setSensitivity(s => s === 'Medium' ? 'High' : 'Medium')} 
                    />
                </View>
            </View>
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        padding: 20,
    },
    header: {
        fontSize: 32,
        fontWeight: '800',
        marginBottom: 24,
    },
    section: {
        marginBottom: 24,
    },
    sectionHeader: {
        fontSize: 14,
        fontWeight: '700',
        color: '#71717A',
        textTransform: 'uppercase',
        letterSpacing: 1,
        marginBottom: 8,
        marginLeft: 4,
    },
    card: {
        borderRadius: 16,
        paddingVertical: 4,
        borderWidth: 1,
        ...Platform.select({
            web: { boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
        })
    },
    item: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingVertical: 16,
        paddingHorizontal: 16,
    },
    itemLeft: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    iconContainer: {
        width: 32,
        height: 32,
        borderRadius: 8,
        alignItems: 'center',
        justifyContent: 'center',
        marginRight: 12,
    },
    itemTitle: {
        fontSize: 16,
        fontWeight: '500',
    },
    itemRight: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    selectContainer: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    selectText: {
        fontSize: 14,
        marginRight: 4,
    },
});
