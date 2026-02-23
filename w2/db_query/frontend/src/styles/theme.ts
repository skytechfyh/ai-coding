/**
 * Apple-inspired design system tokens
 * Following Apple HIG (Human Interface Guidelines) principles
 */

export const colors = {
  // Primary colors - Apple-style
  primary: '#007AFF',
  primaryHover: '#0056CC',
  primaryActive: '#004499',

  // Background colors
  background: {
    primary: '#FFFFFF',
    secondary: '#F5F5F7',
    tertiary: '#F0F0F2',
    elevated: '#FFFFFF',
    sidebar: '#F5F5F7',
  },

  // Text colors
  text: {
    primary: '#1D1D1F',
    secondary: '#86868B',
    tertiary: '#A1A1A6',
    inverse: '#FFFFFF',
  },

  // Border colors
  border: {
    default: '#D2D2D7',
    light: '#E5E5EA',
    medium: '#D1D1D6',
  },

  // Status colors
  status: {
    success: '#34C759',
    warning: '#FF9500',
    error: '#FF3B30',
    info: '#5AC8FA',
  },

  // Database-specific colors (DataGrip-inspired)
  database: {
    postgres: '#336791',
    mysql: '#4479A1',
    sqlite: '#003B57',
    table: '#007AFF',
    view: '#5856D6',
    column: '#34C759',
    index: '#FF9500',
  },

  // SQL syntax highlighting (DataGrip-inspired)
  sql: {
    keyword: '#AF52DE',
    function: '#FF9500',
    string: '#28A745',
    number: '#007AFF',
    comment: '#86868B',
    operator: '#FF3B30',
  },
};

export const spacing = {
  xs: '4px',
  sm: '8px',
  md: '12px',
  lg: '16px',
  xl: '24px',
  xxl: '32px',
  xxxl: '48px',
};

export const typography = {
  // Apple-style font stack
  fontFamily: {
    sans: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif',
    mono: '"SF Mono", "Monaco", "Menlo", "Consolas", monospace',
  },

  fontSize: {
    xs: '11px',
    sm: '12px',
    base: '13px',
    md: '14px',
    lg: '15px',
    xl: '17px',
    xxl: '20px',
    xxxl: '24px',
  },

  fontWeight: {
    regular: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },

  lineHeight: {
    tight: 1.2,
    normal: 1.5,
    relaxed: 1.7,
  },
};

export const shadows = {
  sm: '0 1px 2px rgba(0, 0, 0, 0.05)',
  md: '0 2px 8px rgba(0, 0, 0, 0.08)',
  lg: '0 4px 16px rgba(0, 0, 0, 0.1)',
  xl: '0 8px 32px rgba(0, 0, 0, 0.12)',
};

export const borderRadius = {
  sm: '4px',
  md: '6px',
  lg: '8px',
  xl: '12px',
  full: '9999px',
};

export const transitions = {
  fast: '150ms ease',
  normal: '250ms ease',
  slow: '350ms ease',
};

// Layout dimensions
export const layout = {
  sidebar: {
    width: 220,
    collapsedWidth: 40,
  },
  header: {
    height: 44,
  },
  queryPanel: {
    minHeight: 200,
    maxHeight: '50vh',
  },
  resultsPanel: {
    minHeight: 150,
  },
};

export const theme = {
  colors,
  spacing,
  typography,
  shadows,
  borderRadius,
  transitions,
  layout,
};

export type Theme = typeof theme;
