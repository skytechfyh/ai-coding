/**
 * Monaco Editor theme configuration
 * DataGrip-inspired dark theme
 */

import type { editor } from 'monaco-editor';

export const dataGripTheme: editor.IStandaloneThemeData = {
  base: 'vs',
  inherit: true,
  rules: [
    // Keywords (SELECT, FROM, WHERE, etc.)
    { token: 'keyword.sql', foreground: 'AF52DE', fontStyle: 'bold' },
    { token: 'keyword', foreground: 'AF52DE', fontStyle: 'bold' },

    // Functions (COUNT, SUM, AVG, etc.)
    { token: 'function', foreground: 'FF9500' },
    { token: 'predefined.sql', foreground: 'FF9500' },

    // Strings
    { token: 'string.sql', foreground: '28A745' },
    { token: 'string', foreground: '28A745' },

    // Numbers
    { token: 'number', foreground: '007AFF' },
    { token: 'number.sql', foreground: '007AFF' },

    // Comments
    { token: 'comment', foreground: '86868B', fontStyle: 'italic' },
    { token: 'comment.sql', foreground: '86868B', fontStyle: 'italic' },

    // Operators
    { token: 'operator.sql', foreground: 'FF3B30' },
    { token: 'delimiter', foreground: '86868B' },

    // Identifiers (table names, column names)
    { token: 'identifier.sql', foreground: '1D1D1F' },
    { token: 'identifier', foreground: '1D1D1F' },

    // Type
    { token: 'type', foreground: '5AC8FA' },

    // Variables
    { token: 'variable', foreground: 'FF9500' },
    { token: 'variable.predefined', foreground: 'FF9500' },

    // Constants
    { token: 'constant', foreground: '007AFF' },

    // Punctuation
    { token: 'delimiter.bracket', foreground: '86868B' },
    { token: 'delimiter.parenthesis', foreground: '86868B' },
  ],
  colors: {
    // Background
    'editor.background': '#FFFFFF',
    'editor.foreground': '#1D1D1F',

    // Cursor
    'editorCursor.foreground': '#007AFF',

    // Selection - use Apple blue, more subtle
    'editor.selectionBackground': 'rgba(0, 122, 255, 0.15)',
    'editor.inactiveSelectionBackground': 'rgba(0, 122, 255, 0.08)',

    // Current line highlight
    'editor.lineHighlightBackground': '#F5F5F7',
    'editor.lineHighlightBorder': '#E5E5EA',

    // Line numbers
    'editorLineNumber.foreground': '#A1A1A6',
    'editorLineNumber.activeForeground': '#86868B',

    // Whitespace
    'editorWhitespace.foreground': '#D2D2D7',

    // Indent guides
    'editorIndentGuide.background': '#E5E5EA',
    'editorIndentGuide.activeBackground': '#D2D2D7',

    // Brackets
    'editorBracketMatch.background': 'rgba(0, 122, 255, 0.08)',
    'editorBracketMatch.border': '#007AFF',

    // Search
    'editor.findMatchBackground': 'rgba(255, 204, 0, 0.3)',
    'editor.findMatchHighlightBackground': 'rgba(255, 204, 0, 0.15)',

    // Scrollbar
    'scrollbarSlider.background': 'rgba(0, 0, 0, 0.1)',
    'scrollbarSlider.hoverBackground': 'rgba(0, 0, 0, 0.2)',
    'scrollbarSlider.activeBackground': 'rgba(0, 0, 0, 0.3)',

    // Minimap
    'minimap.background': '#F5F5F7',
    'minimap.selectionHighlight': 'rgba(0, 122, 255, 0.15)',

    // Error/warning
    'editorError.foreground': '#FF3B30',
    'editorWarning.foreground': '#FF9500',

    // Links
    'editorLink.activeForeground': '#007AFF',
  },
};

// Theme name constant
export const THEME_NAME = 'datagrip-light';
