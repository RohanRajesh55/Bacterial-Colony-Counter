import 'react-native-gesture-handler';
import React from 'react';
import { NavigationContainer, DefaultTheme, DarkTheme } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createDrawerNavigator, DrawerContentScrollView, DrawerItemList } from '@react-navigation/drawer';
import { Ionicons } from '@expo/vector-icons';
import { Platform, View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { ThemeProvider, useTheme } from './src/context/ThemeContext';

// Screens
import HomeScreen from './src/screens/HomeScreen';
import CameraScreen from './src/screens/CameraScreen';
import ResultScreen from './src/screens/ResultScreen';
import AboutScreen from './src/screens/AboutScreen';
import SettingsScreen from './src/screens/SettingsScreen';
import HistoryScreen from './src/screens/HistoryScreen'; // Import correctly

const Stack = createNativeStackNavigator();
const Drawer = createDrawerNavigator();

// --- Components ---

function CustomDrawerContent(props) {
  const { theme, isDark } = useTheme();
  const colors = theme.colors;

  return (
    <View style={{ flex: 1, backgroundColor: colors.background }}>
      {/* Drawer Header */}
      <View style={[styles.drawerHeader, { backgroundColor: colors.card }]}>
        <View style={[styles.avatarContainer, { backgroundColor: isDark ? '#431407' : '#FFF7ED', borderColor: colors.primary }]}>
           <Ionicons name="flask" size={32} color={colors.primary} />
        </View>
        <View>
            <Text style={[styles.drawerTitle, { color: colors.text }]}>Colony Counter</Text>
            <Text style={[styles.drawerSubtitle, { color: colors.subtext }]}>Analyzed: 14 plates</Text>
        </View>
      </View>

      <View style={[styles.divider, { backgroundColor: colors.border }]} />

      {/* Drawer Items */}
      <DrawerContentScrollView {...props} contentContainerStyle={{ paddingTop: 10 }}>
        <DrawerItemList {...props} />
      </DrawerContentScrollView>

      {/* Drawer Footer */}
      <View style={[styles.drawerFooter, { backgroundColor: colors.background, borderTopColor: colors.border }]}>
        <TouchableOpacity style={styles.footerItem}>
             <Ionicons name="log-out-outline" size={24} color={colors.subtext} />
             <Text style={[styles.footerText, { color: colors.subtext }]}>Sign Out</Text>
        </TouchableOpacity>
        <Text style={[styles.versionText, { color: colors.subtext }]}>v1.0.0 • Alpha</Text>
      </View>
    </View>
  );
}

// Stack for the Analyzer process
function AnalyzerStack() {
  const { theme } = useTheme();
  return (
    <Stack.Navigator initialRouteName="Home">
      <Stack.Screen name="Home" component={HomeScreen} options={{ headerShown: false }} />
      <Stack.Screen name="Camera" component={CameraScreen} options={{ headerShown: false }} />
      <Stack.Screen name="Result" component={ResultScreen} options={{ 
          title: 'Results',
          headerShown: true, 
          headerStyle: { backgroundColor: theme.colors.background },
          headerTintColor: theme.colors.text,
      }} />
    </Stack.Navigator>
  );
}

// Wrapper component to access theme for Navigation styling
function MainApp() {
    const { theme, isDark } = useTheme();
    const colors = theme.colors;
    const baseTheme = isDark ? DarkTheme : DefaultTheme;

    return (
        <NavigationContainer theme={{
            ...baseTheme,
            colors: {
                ...baseTheme.colors,
                primary: colors.primary,
                background: colors.background,
                card: colors.card,
                text: colors.text,
                border: colors.border,
                notification: colors.primary,
            }
        }}>
          <Drawer.Navigator
            drawerContent={(props) => <CustomDrawerContent {...props} />}
            screenOptions={{
              headerStyle: {
                  backgroundColor: colors.background,
                  borderBottomWidth: 1,
                  borderBottomColor: colors.border,
              },
              headerTintColor: colors.text,
              headerTitleStyle: {
                  fontWeight: '800',
                  color: colors.text,
              },
              drawerActiveTintColor: colors.primary,
              drawerInactiveTintColor: colors.subtext,
              drawerActiveBackgroundColor: isDark ? '#431407' : '#FFF7ED',
              drawerType: 'front',
              drawerStyle: {
                  backgroundColor: colors.card,
                  width: 280,
              },
              drawerLabelStyle: {
                  fontWeight: '600',
                  marginLeft: -10,
              },
              drawerItemStyle: {
                  borderRadius: 8,
                  marginHorizontal: 10,
                  marginVertical: 4,
              }
            }}
          >
            <Drawer.Screen 
                name="Analyzer" 
                component={AnalyzerStack} 
                options={{ 
                    title: 'Colony Counter',
                    drawerLabel: 'Analyze',
                    drawerIcon: ({ color, size }) => (
                        <Ionicons name="scan-circle" size={size} color={color} />
                    ),
                }}
            />
            <Drawer.Screen 
                name="History" 
                component={HistoryScreen} 
                options={{
                    drawerIcon: ({ color, size }) => (
                        <Ionicons name="time" size={size} color={color} />
                    ),
                }}
            />
            <Drawer.Screen 
                name="Settings" 
                component={SettingsScreen} 
                options={{
                    drawerIcon: ({ color, size }) => (
                        <Ionicons name="settings" size={size} color={color} />
                    ),
                }}
            />
            <Drawer.Screen 
                name="About" 
                component={AboutScreen} 
                options={{ 
                    title: 'About CFD',
                    drawerIcon: ({ color, size }) => (
                        <Ionicons name="information-circle" size={size} color={color} />
                    ),
                }}
            />
          </Drawer.Navigator>
        </NavigationContainer>
    );
}

export default function App() {
  return (
    <ThemeProvider>
        <MainApp />
    </ThemeProvider>
  );
}

const styles = StyleSheet.create({
    drawerHeader: {
        padding: 24,
        paddingTop: 48,
        flexDirection: 'row',
        alignItems: 'center',
    },
    avatarContainer: {
        width: 48,
        height: 48,
        borderRadius: 24,
        alignItems: 'center',
        justifyContent: 'center',
        marginRight: 16,
        borderWidth: 1,
    },
    drawerTitle: {
        fontSize: 18,
        fontWeight: '800',
    },
    drawerSubtitle: {
        fontSize: 13,
        marginTop: 2,
    },
    divider: {
        height: 1,
        width: '100%',
    },
    drawerFooter: {
        padding: 20,
        borderTopWidth: 1,
    },
    footerItem: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 16,
    },
    footerText: {
        fontSize: 16,
        fontWeight: '600',
        marginLeft: 12,
    },
    versionText: {
        fontSize: 12,
        textAlign: 'center',
    }
});
