import React, { useState, useCallback } from 'react';
import { View, Text, StyleSheet, FlatList, Image, TouchableOpacity, Alert } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../context/ThemeContext';

export default function HistoryScreen() {
  const { theme } = useTheme();
  const colors = theme.colors;
  const navigation = useNavigation();
  const [history, setHistory] = useState([]);

  useFocusEffect(
    useCallback(() => {
      loadHistory();
    }, [])
  );

  const loadHistory = async () => {
    try {
      const stored = await AsyncStorage.getItem('scan_history');
      if (stored) {
        setHistory(JSON.parse(stored).reverse()); // Newest first
      }
    } catch (e) {
      console.error(e);
    }
  };

  const clearHistory = async () => {
      Alert.alert(
          "Clear History",
          "Are you sure you want to delete all records?",
          [
              { text: "Cancel", style: "cancel" },
              { text: "Delete", style: "destructive", onPress: async () => {
                  await AsyncStorage.removeItem('scan_history');
                  setHistory([]);
              }}
          ]
      );
  };

  const renderItem = ({ item }) => (
    <TouchableOpacity 
        style={[styles.card, { backgroundColor: colors.card, borderColor: colors.border }]}
        onPress={() => navigation.navigate('Result', { result: item })}
    >
        <Image source={{ uri: item.thumbnail }} style={styles.thumbnail} />
        <View style={styles.info}>
            <View style={styles.row}>
                <Text style={[styles.count, { color: colors.text }]}>{item.count} Colonies</Text>
                <View style={styles.badge}>
                    <Text style={styles.badgeText}>COMPLETED</Text>
                </View>
            </View>
            <Text style={[styles.date, { color: colors.subtext }]}>
                {new Date(item.date).toLocaleDateString(undefined, { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' })}
            </Text>
            <Text style={[styles.time, { color: colors.subtext }]}>
                {new Date(item.date).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})} • ID: {item.id.slice(-4)}
            </Text>
        </View>
        <Ionicons name="chevron-forward" size={20} color={colors.subtext} />
    </TouchableOpacity>
  );

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <View style={styles.header}>
          <Text style={[styles.headerTitle, { color: colors.text }]}>Recent Analysis</Text>
          {history.length > 0 && (
              <TouchableOpacity onPress={clearHistory}>
                  <Text style={[styles.clearText, { color: colors.primary }]}>Clear All</Text>
              </TouchableOpacity>
          )}
      </View>

      {history.length === 0 ? (
          <View style={styles.emptyContainer}>
               <View style={[styles.iconCircle, { backgroundColor: theme.dark ? '#333' : '#F4F4F5' }]}>
                    <Ionicons name="clipboard-outline" size={48} color={colors.subtext} />
               </View>
               <Text style={[styles.emptyText, { color: colors.text }]}>No history found</Text>
               <Text style={[styles.emptySub, { color: colors.subtext }]}>Complete an analysis to see it here.</Text>
          </View>
      ) : (
          <FlatList
            data={history}
            keyExtractor={(item) => item.id}
            renderItem={renderItem}
            contentContainerStyle={styles.listContent}
            showsVerticalScrollIndicator={false}
          />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'center',
      paddingHorizontal: 20,
      paddingTop: 20,
      paddingBottom: 10,
  },
  headerTitle: {
      fontSize: 20,
      fontWeight: '700',
      letterSpacing: -0.5,
  },
  clearText: {
      fontSize: 14,
      fontWeight: '600',
  },
  listContent: {
    padding: 20,
  },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderRadius: 16,
    marginBottom: 12,
    borderWidth: 1,
  },
  thumbnail: {
    width: 64,
    height: 64,
    borderRadius: 12,
    backgroundColor: '#F4F4F5',
  },
  info: {
    flex: 1,
    marginLeft: 16,
  },
  row: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginBottom: 4,
  },
  count: {
    fontSize: 16,
    fontWeight: '700',
  },
  badge: {
      backgroundColor: '#DCFCE7', // Light green
      paddingHorizontal: 6,
      paddingVertical: 2,
      borderRadius: 4,
  },
  badgeText: {
      fontSize: 10,
      fontWeight: '700',
      color: '#166534',
  },
  date: {
    fontSize: 13,
    marginBottom: 2,
  },
  time: {
      fontSize: 12,
      opacity: 0.7,
  },
  emptyContainer: {
      flex: 1,
      justifyContent: 'center',
      alignItems: 'center',
      marginTop: -40,
  },
  iconCircle: {
      width: 100,
      height: 100,
      borderRadius: 50,
      alignItems: 'center',
      justifyContent: 'center',
      marginBottom: 24,
  },
  emptyText: {
      fontSize: 18, 
      fontWeight: '600',
      marginBottom: 8,
  },
  emptySub: {
      fontSize: 14,
  }
});
