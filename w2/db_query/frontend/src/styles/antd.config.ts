/**
 * Ant Design theme configuration
 * Apple-inspired design with DataGrip functionality
 */

import type { ThemeConfig } from 'antd';

export const antdTheme: ThemeConfig = {
  token: {
    // Apple-style typography
    fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif',
    fontSize: 13,
    fontSizeHeading1: 24,
    fontSizeHeading2: 20,
    fontSizeHeading3: 17,
    fontSizeHeading4: 15,
    fontSizeHeading5: 14,

    // Colors
    colorPrimary: '#007AFF',
    colorSuccess: '#34C759',
    colorWarning: '#FF9500',
    colorError: '#FF3B30',
    colorInfo: '#5AC8FA',

    // Background colors
    colorBgContainer: '#FFFFFF',
    colorBgElevated: '#FFFFFF',
    colorBgLayout: '#F5F5F7',
    colorBgSpotlight: '#F0F0F2',

    // Text colors
    colorText: '#1D1D1F',
    colorTextSecondary: '#86868B',
    colorTextTertiary: '#A1A1A6',

    // Border
    colorBorder: '#D2D2D7',
    colorBorderSecondary: '#E5E5EA',

    // Spacing
    padding: 12,
    paddingLG: 16,
    paddingSM: 8,
    margin: 12,
    marginLG: 16,
    marginSM: 8,

    // Border radius - Apple-style
    borderRadius: 6,
    borderRadiusLG: 8,
    borderRadiusSM: 4,

    // Shadows
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)',
    boxShadowSecondary: '0 4px 16px rgba(0, 0, 0, 0.1)',

    // Line heights
    lineHeight: 1.5,
    lineHeightHeading1: 1.2,
    lineHeightHeading2: 1.3,
    lineHeightHeading3: 1.4,

    // Control heights
    controlHeight: 32,
    controlHeightLG: 40,
    controlHeightSM: 24,
  },

  components: {
    Layout: {
      headerBg: '#FFFFFF',
      bodyBg: '#F5F5F7',
      siderBg: '#F5F5F7',
      headerHeight: 52,
      headerPadding: '0 16px',
    },

    Menu: {
      itemBg: 'transparent',
      itemSelectedBg: 'rgba(0, 122, 255, 0.1)',
      itemSelectedColor: '#007AFF',
      itemHoverBg: 'rgba(0, 0, 0, 0.04)',
      itemMarginInline: 8,
      itemPaddingInline: 12,
      iconSize: 14,
    },

    Card: {
      borderRadiusLG: 8,
      paddingLG: 16,
      boxShadowTertiary: '0 1px 2px rgba(0, 0, 0, 0.05)',
    },

    Button: {
      borderRadius: 6,
      controlHeight: 32,
      paddingInline: 16,
      fontWeight: 500,
    },

    Input: {
      borderRadius: 6,
      controlHeight: 32,
    },

    Select: {
      borderRadius: 6,
      controlHeight: 32,
    },

    Table: {
      borderRadius: 8,
      headerBg: '#F5F5F7',
      headerColor: '#86868B',
      rowHoverBg: 'rgba(0, 122, 255, 0.04)',
      borderColor: '#E5E5EA',
    },

    Tree: {
      directoryNodeSelectedBg: 'rgba(0, 122, 255, 0.1)',
      directoryNodeSelectedColor: '#007AFF',
    },

    Tabs: {
      inkBarColor: '#007AFF',
      itemSelectedColor: '#007AFF',
      itemHoverColor: '#0056CC',
    },

    Modal: {
      borderRadiusLG: 12,
      titleFontSize: 17,
    },

    Message: {
      contentPadding: '12px 16px',
      borderRadiusLG: 8,
    },

    Tooltip: {
      borderRadius: 6,
    },

    Collapse: {
      borderRadiusLG: 8,
      headerPadding: '12px 16px',
    },

    List: {
      padding: 12,
    },

    Spin: {
      dotSizeLG: 24,
    },
  },
};
