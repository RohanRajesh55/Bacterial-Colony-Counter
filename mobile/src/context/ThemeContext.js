import React, { createContext, useState, useContext, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

const ThemeContext = createContext();

export const lightTheme = {
  dark: false,
  colors: {
    background: '#FAFAFA',
    card: '#FFFFFF',
    text: '#18181B',
    subtext: '#52525B',
    border: '#E4E4E7',
    primary: '#F97316', // Coral
    secondary: '#0EA5E9', // Blue
    input: '#F4F4F5',
  },
};

export const darkTheme = {
  dark: true,
  colors: {
    background: '#18181B', // Zinc 900
    card: '#27272A', // Zinc 800
    text: '#FAFAFA', // Zinc 50
    subtext: '#A1A1AA', // Zinc 400
    border: '#3F3F46', // Zinc 700
    primary: '#FB923C', // Orange 400 (Ligher for dark mode)
    secondary: '#38BDF8', // Sky 400
    input: '#3F3F46',
  },
};

export const ThemeProvider = ({ children }) => {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    // Load saved theme
    AsyncStorage.getItem('theme').then(value => {
      if (value === 'dark') setIsDark(true);
    });
  }, []);

  const toggleTheme = () => {
    setIsDark(prev => {
      const newVal = !prev;
      AsyncStorage.setItem('theme', newVal ? 'dark' : 'light');
      return newVal;
    });
  };

  const theme = isDark ? darkTheme : lightTheme;

  return (
    <ThemeContext.Provider value={{ theme, isDark, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => useContext(ThemeContext);
