/**
 * SQL Completion Provider for Monaco Editor
 * Provides SQL keywords, functions, and table/column suggestions
 */

import type { languages, IDisposable } from "monaco-editor";

// SQL Keywords
const SQL_KEYWORDS = [
  "SELECT", "FROM", "WHERE", "AND", "OR", "IN", "NOT", "LIKE", "BETWEEN",
  "IS", "NULL", "TRUE", "FALSE", "AS", "ON", "JOIN", "LEFT", "RIGHT",
  "INNER", "OUTER", "FULL", "CROSS", "NATURAL", "USING", "ORDER", "BY",
  "ASC", "DESC", "LIMIT", "OFFSET", "GROUP", "HAVING", "UNION", "ALL",
  "DISTINCT", "CASE", "WHEN", "THEN", "ELSE", "END", "EXISTS", "ANY",
  "SOME", "OVER", "PARTITION", "ROW", "ROWS", "RANGE", "PRECEDING",
  "FOLLOWING", "CURRENT", "UNBOUNDED", "NULLS", "FIRST", "LAST",
  "WITH", "RECURSIVE", "ESCAPE", "COLLATE", "NATIONAL", "CHARACTER",
];

// SQL Functions
const SQL_FUNCTIONS = [
  // Aggregate functions
  "COUNT", "SUM", "AVG", "MIN", "MAX", "ARRAY_AGG", "STRING_AGG",
  "BOOL_AND", "BOOL_OR", "EVERY", "COALESCE", "NULLIF", "GREATEST",
  "LEAST", "ROW_NUMBER", "RANK", "DENSE_RANK", "NTILE", "LAG", "LEAD",
  "FIRST_VALUE", "LAST_VALUE", "NTH_VALUE",
  // String functions
  "LOWER", "UPPER", "TRIM", "LTRIM", "RTRIM", "SUBSTRING", "SUBSTR",
  "LENGTH", "CHAR_LENGTH", "OCTET_LENGTH", "POSITION", "REPLACE", "CONCAT",
  "CONCAT_WS", "LEFT", "RIGHT", "LPAD", "RPAD", "REVERSE", "SPLIT_PART",
  // Number functions
  "ABS", "CEIL", "CEILING", "FLOOR", "ROUND", "TRUNC", "MOD", "POWER",
  "SQRT", "RANDOM", "SIGN",
  // Date/Time functions
  "NOW", "CURRENT_TIMESTAMP", "CURRENT_DATE", "CURRENT_TIME", "EXTRACT",
  "DATE_PART", "DATE_TRUNC", "AGE", "MAKE_DATE", "MAKE_TIME", "MAKE_TIMESTAMP",
  // Type conversion
  "CAST", "TO_CHAR", "TO_DATE", "TO_TIMESTAMP", "TO_NUMBER",
  // JSON functions
  "JSON_BUILD_OBJECT", "JSON_BUILD_ARRAY", "JSON_OBJECT", "JSON_ARRAY",
  "JSON_EXTRACT_PATH", "->>", "#>", "#>>",
  // Other
  "GENERATE_SERIES", "ARRAY", "UNNEST",
];

// SQL Data Types
const SQL_TYPES = [
  "INTEGER", "INT", "SMALLINT", "BIGINT", "SERIAL", "BIGSERIAL",
  "REAL", "DOUBLE", "PRECISION", "DECIMAL", "NUMERIC", "FLOAT",
  "CHAR", "CHARACTER", "VARCHAR", "TEXT", "BOOLEAN", "DATE",
  "TIME", "TIMESTAMP", "TIMESTAMPTZ", "INTERVAL", "UUID", "JSON",
  "JSONB", "XML", "POINT", "LINE", "CIRCLE", "BOX", "PATH",
  "POLYGON", "INET", "CIDR", "MACADDR", "BYTEA", "ARRAY",
];

export function registerSqlCompletionProvider(
  monaco: typeof import("monaco-editor")
): IDisposable {
  // Register SQL language if not already registered
  if (!monaco.languages.getLanguages().some((lang) => lang.id === "sql")) {
    monaco.languages.register({ id: "sql" });
  }

  // Register completion provider
  const disposable = monaco.languages.registerCompletionItemProvider("sql", {
    triggerCharacters: [" ", ".", ","],
    provideCompletionItems: (model, position) => {
      const word = model.getWordUntilPosition(position);
      const range = {
        startLineNumber: position.lineNumber,
        endLineNumber: position.lineNumber,
        startColumn: word.startColumn,
        endColumn: word.endColumn,
      };

      const suggestions: languages.CompletionItem[] = [];

      // Add keywords
      SQL_KEYWORDS.forEach((keyword) => {
        suggestions.push({
          label: keyword,
          kind: monaco.languages.CompletionItemKind.Keyword,
          insertText: keyword,
          range,
          detail: "Keyword",
        });
      });

      // Add functions
      SQL_FUNCTIONS.forEach((fn) => {
        suggestions.push({
          label: fn,
          kind: monaco.languages.CompletionItemKind.Function,
          insertText: fn + "($0)",
          insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
          range,
          detail: "Function",
        });
      });

      // Add data types
      SQL_TYPES.forEach((type) => {
        suggestions.push({
          label: type,
          kind: monaco.languages.CompletionItemKind.Class,
          insertText: type,
          range,
          detail: "Data Type",
        });
      });

      return { suggestions };
    },
  });

  return disposable;
}
