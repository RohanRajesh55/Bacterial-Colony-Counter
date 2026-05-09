import React from 'react';
import { View, StyleSheet, Dimensions } from 'react-native';
import Svg, { Circle, Ellipse, Path, Defs, LinearGradient, Stop, RadialGradient } from 'react-native-svg';
import { useTheme } from '../context/ThemeContext';

const { width, height } = Dimensions.get('window');

// Floating bacteria/colony shapes as decorative elements
const BacteriaShape = ({ cx, cy, rx, ry, rotation, color, opacity }) => (
  <Ellipse
    cx={cx}
    cy={cy}
    rx={rx}
    ry={ry}
    fill={color}
    opacity={opacity}
    transform={`rotate(${rotation} ${cx} ${cy})`}
  />
);

const ColonyCluster = ({ x, y, size, color, opacity }) => (
  <>
    <Circle cx={x} cy={y} r={size} fill={color} opacity={opacity} />
    <Circle cx={x + size * 0.6} cy={y - size * 0.4} r={size * 0.5} fill={color} opacity={opacity * 0.8} />
    <Circle cx={x - size * 0.5} cy={y + size * 0.3} r={size * 0.4} fill={color} opacity={opacity * 0.7} />
  </>
);

// Petri dish ring decoration
const PetriDishRing = ({ cx, cy, radius, color, opacity }) => (
  <>
    <Circle cx={cx} cy={cy} r={radius} stroke={color} strokeWidth={2} fill="none" opacity={opacity} />
    <Circle cx={cx} cy={cy} r={radius * 0.85} stroke={color} strokeWidth={1} fill="none" opacity={opacity * 0.5} />
  </>
);

export default function ThemedBackground({ children, style, variant = 'default' }) {
  const { theme, isDark } = useTheme();
  const colors = theme.colors;

  // Theme-based decoration colors
  const decorColors = isDark ? {
    primary: '#FB923C',    // Orange
    secondary: '#38BDF8',  // Sky blue
    accent: '#A78BFA',     // Purple
    subtle: '#52525B',     // Muted
    glow: '#431407',       // Dark orange glow
  } : {
    primary: '#F97316',    // Orange
    secondary: '#0EA5E9',  // Blue
    accent: '#8B5CF6',     // Purple
    subtle: '#D4D4D8',     // Muted gray
    glow: '#FFF7ED',       // Light orange glow
  };

  return (
    <View style={[styles.container, { backgroundColor: colors.background }, style]}>
      {/* Background SVG Decorations */}
      <View style={styles.svgContainer} pointerEvents="none">
        <Svg width={width} height={height} style={styles.svg}>
          <Defs>
            {/* Gradient for background glow */}
            <RadialGradient id="centerGlow" cx="50%" cy="30%" r="60%">
              <Stop offset="0%" stopColor={decorColors.glow} stopOpacity={isDark ? 0.4 : 0.6} />
              <Stop offset="100%" stopColor={colors.background} stopOpacity={0} />
            </RadialGradient>
            
            {/* Primary accent gradient */}
            <LinearGradient id="primaryGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <Stop offset="0%" stopColor={decorColors.primary} stopOpacity={0.3} />
              <Stop offset="100%" stopColor={decorColors.secondary} stopOpacity={0.1} />
            </LinearGradient>
          </Defs>

          {/* Central glow */}
          <Circle cx={width / 2} cy={height * 0.3} r={width * 0.8} fill="url(#centerGlow)" />

          {/* Decorative petri dish rings */}
          <PetriDishRing cx={width * 0.85} cy={height * 0.12} radius={60} color={decorColors.primary} opacity={0.15} />
          <PetriDishRing cx={width * 0.1} cy={height * 0.75} radius={80} color={decorColors.secondary} opacity={0.12} />
          <PetriDishRing cx={width * 0.9} cy={height * 0.85} radius={45} color={decorColors.accent} opacity={0.1} />

          {/* Floating colony clusters */}
          <ColonyCluster x={width * 0.08} y={height * 0.15} size={12} color={decorColors.primary} opacity={0.2} />
          <ColonyCluster x={width * 0.92} y={height * 0.35} size={8} color={decorColors.secondary} opacity={0.15} />
          <ColonyCluster x={width * 0.15} y={height * 0.55} size={10} color={decorColors.accent} opacity={0.12} />
          <ColonyCluster x={width * 0.85} y={height * 0.65} size={14} color={decorColors.primary} opacity={0.18} />
          <ColonyCluster x={width * 0.05} y={height * 0.88} size={9} color={decorColors.secondary} opacity={0.14} />

          {/* Bacteria shapes scattered around */}
          <BacteriaShape cx={width * 0.2} cy={height * 0.08} rx={18} ry={6} rotation={-30} color={decorColors.subtle} opacity={0.25} />
          <BacteriaShape cx={width * 0.75} cy={height * 0.22} rx={14} ry={5} rotation={45} color={decorColors.subtle} opacity={0.2} />
          <BacteriaShape cx={width * 0.9} cy={height * 0.48} rx={16} ry={5} rotation={-15} color={decorColors.subtle} opacity={0.18} />
          <BacteriaShape cx={width * 0.12} cy={height * 0.42} rx={12} ry={4} rotation={60} color={decorColors.subtle} opacity={0.22} />
          <BacteriaShape cx={width * 0.65} cy={height * 0.78} rx={20} ry={6} rotation={30} color={decorColors.subtle} opacity={0.15} />
          <BacteriaShape cx={width * 0.3} cy={height * 0.92} rx={15} ry={5} rotation={-45} color={decorColors.subtle} opacity={0.2} />

          {/* Small dots representing colonies */}
          <Circle cx={width * 0.25} cy={height * 0.18} r={3} fill={decorColors.primary} opacity={0.3} />
          <Circle cx={width * 0.7} cy={height * 0.12} r={4} fill={decorColors.secondary} opacity={0.25} />
          <Circle cx={width * 0.55} cy={height * 0.28} r={2} fill={decorColors.accent} opacity={0.35} />
          <Circle cx={width * 0.4} cy={height * 0.72} r={3} fill={decorColors.primary} opacity={0.28} />
          <Circle cx={width * 0.8} cy={height * 0.58} r={4} fill={decorColors.secondary} opacity={0.22} />
          <Circle cx={width * 0.35} cy={height * 0.45} r={2} fill={decorColors.accent} opacity={0.3} />
          <Circle cx={width * 0.6} cy={height * 0.88} r={3} fill={decorColors.primary} opacity={0.25} />
          <Circle cx={width * 0.18} cy={height * 0.68} r={2} fill={decorColors.secondary} opacity={0.32} />

          {/* Microscope grid pattern - subtle */}
          {variant === 'grid' && (
            <>
              {[...Array(8)].map((_, i) => (
                <Path
                  key={`h-${i}`}
                  d={`M 0 ${(height / 8) * i} L ${width} ${(height / 8) * i}`}
                  stroke={decorColors.subtle}
                  strokeWidth={0.5}
                  opacity={0.1}
                />
              ))}
              {[...Array(6)].map((_, i) => (
                <Path
                  key={`v-${i}`}
                  d={`M ${(width / 6) * i} 0 L ${(width / 6) * i} ${height}`}
                  stroke={decorColors.subtle}
                  strokeWidth={0.5}
                  opacity={0.1}
                />
              ))}
            </>
          )}
        </Svg>
      </View>

      {/* Content */}
      <View style={styles.content}>
        {children}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  svgContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    zIndex: 0,
  },
  svg: {
    position: 'absolute',
    top: 0,
    left: 0,
  },
  content: {
    flex: 1,
    zIndex: 1,
  },
});
