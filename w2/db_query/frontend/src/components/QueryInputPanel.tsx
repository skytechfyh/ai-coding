/**
 * Query Input Panel - Unified input for both SQL and natural language
 * Automatically detects whether input is natural language or SQL
 */
import { useState, useRef, useEffect } from "react";
import { Button, Empty, Space, Tabs, Typography, message } from "antd";
import { PlayCircleOutlined, PlusOutlined, CloseOutlined, ThunderboltOutlined } from "@ant-design/icons";
import Editor from "@monaco-editor/react";
import type { editor } from "monaco-editor";

import { dataGripTheme, THEME_NAME } from "../styles/monaco-theme";
import { registerSqlCompletionProvider } from "../styles/sql-completion";
import { apiService } from "../services/api";
import type { QueryTab } from "../types";

const { Text } = Typography;

interface QueryInputPanelProps {
  tabs: QueryTab[];
  activeTabId: string;
  onTabChange: (tabId: string) => void;
  onTabAdd: () => void;
  onTabClose: (tabId: string) => void;
  onTabUpdate: (tabId: string, sql: string) => void;
  onExecute: (tabId: string, sql?: string) => void;
  executingTabId: string | null;
  databaseName: string | null;
}

// Simple heuristic to detect if text is natural language vs SQL
function isNaturalLanguage(text: string): boolean {
  const sqlKeywords = ['SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER', 'JOIN', 'GROUP BY', 'ORDER BY', 'HAVING', 'LIMIT'];
  const upperText = text.toUpperCase();

  // If it starts with common SQL keywords, treat as SQL
  for (const keyword of sqlKeywords) {
    if (upperText.includes(keyword)) {
      return false;
    }
  }

  // If it's short and contains natural language patterns, treat as natural language
  if (text.length < 200) {
    // Check for natural language patterns
    const nlPatterns = [/^(show|get|find|list|display|query)/i, /^(what|how|which|who|when|where)/i, /^(给我|查询|显示|查找)/];
    for (const pattern of nlPatterns) {
      if (pattern.test(text.trim())) {
        return true;
      }
    }
  }

  // Default to natural language if no SQL keywords found
  return true;
}

export function QueryInputPanel({
  tabs,
  activeTabId,
  onTabChange,
  onTabAdd,
  onTabClose,
  onTabUpdate,
  onExecute,
  executingTabId,
  databaseName,
}: QueryInputPanelProps) {
  const editorRefs = useRef<Record<string, editor.IStandaloneCodeEditor>>({});
  const completionProviderRef = useRef<unknown>(null);
  const [aiLoading, setAiLoading] = useState(false);

  // Register SQL completion provider once
  useEffect(() => {
    const monaco = (window as unknown as { monaco: typeof import("monaco-editor") }).monaco;
    if (monaco && !completionProviderRef.current) {
      completionProviderRef.current = registerSqlCompletionProvider(monaco);
    }

    return () => {
      if (completionProviderRef.current) {
        (completionProviderRef.current as { dispose: () => void }).dispose();
        completionProviderRef.current = null;
      }
    };
  }, []);

  const handleEditorMount = (tabId: string, editorInstance: editor.IStandaloneCodeEditor) => {
    editorRefs.current[tabId] = editorInstance;

    // Define custom theme
    const monaco = (window as unknown as { monaco: typeof import("monaco-editor") }).monaco;
    if (monaco) {
      monaco.editor.defineTheme(THEME_NAME, dataGripTheme);
      monaco.editor.setTheme(THEME_NAME);
    }

    // Add keyboard shortcut for Ctrl+Enter / Cmd+Enter
    editorInstance.addCommand(
      2048 | 3, // Monaco.KeyMod.CtrlCmd | Monaco.KeyCode.Enter
      () => {
        handleRunWithAI(tabId);
      }
    );

    editorInstance.focus();
  };

  const handleRunWithAI = async (tabId: string) => {
    const tab = tabs.find((t) => t.id === tabId);
    if (!tab?.sql.trim() || !databaseName) return;

    // Check if input is natural language
    if (isNaturalLanguage(tab.sql)) {
      // Use AI to generate SQL
      setAiLoading(true);
      try {
        const result = await apiService.generateSql(databaseName, tab.sql);
        // Update the tab with generated SQL
        onTabUpdate(tabId, result.sql);
        message.success("SQL generated, executing...");
        // Execute the generated SQL directly
        onExecute(tabId, result.sql);
      } catch (error) {
        message.error(`Failed to generate SQL: ${error}`);
      } finally {
        setAiLoading(false);
      }
    } else {
      // Execute as SQL directly
      onExecute(tabId);
    }
  };

  const activeTab = tabs.find((t) => t.id === activeTabId);

  const tabItems = tabs.map((tab) => ({
    key: tab.id,
    label: (
      <div className="tab-label">
        <span className="tab-name">{tab.name}</span>
        {tab.isDirty && <span className="tab-dirty">*</span>}
        {tabs.length > 1 && (
          <CloseOutlined
            className="tab-close"
            onClick={(e) => {
              e.stopPropagation();
              onTabClose(tab.id);
            }}
          />
        )}
      </div>
    ),
    children: (
      <div className="editor-container">
        <Editor
          height="100%"
          defaultLanguage="sql"
          value={tab.sql}
          onChange={(val) => onTabUpdate(tab.id, val || "")}
          onMount={(editorInstance) => handleEditorMount(tab.id, editorInstance)}
          options={{
            minimap: { enabled: false },
            fontSize: 13,
            fontFamily: '"SF Mono", Monaco, Menlo, Consolas, monospace',
            lineNumbers: "on",
            lineHeight: 20,
            scrollBeyondLastLine: false,
            automaticLayout: true,
            tabSize: 2,
            wordWrap: "on",
            folding: true,
            scrollbar: { verticalScrollbarSize: 8, horizontalScrollbarSize: 8 },
            padding: { top: 8, bottom: 8 },
            quickSuggestions: true,
            suggestOnTriggerCharacters: true,
          }}
        />
      </div>
    ),
  }));

  const isAILoading = aiLoading || (executingTabId === activeTabId);

  return (
    <div className="query-input-panel">
      {/* Toolbar */}
      <div className="editor-toolbar">
        <Space>
          <Button
            type="primary"
            icon={isAILoading ? <ThunderboltOutlined spin /> : <PlayCircleOutlined />}
            onClick={() => activeTabId && handleRunWithAI(activeTabId)}
            loading={isAILoading}
            disabled={!activeTab?.sql.trim() || !databaseName}
            size="small"
          >
            Run
          </Button>
          <Text type="secondary" className="hint-text">
            Enter SQL or natural language, press Ctrl+Enter
          </Text>
        </Space>
        <Space>
          <Button
            type="text"
            icon={<PlusOutlined />}
            onClick={onTabAdd}
            size="small"
          />
        </Space>
      </div>

      {/* Tabs and Editor */}
      <div className="editor-area">
        {tabs.length === 0 ? (
          <div className="empty-editor">
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No query tabs">
              <Button type="primary" onClick={onTabAdd}>
                <PlusOutlined /> New Query
              </Button>
            </Empty>
          </div>
        ) : (
          <Tabs
            activeKey={activeTabId}
            onChange={onTabChange}
            items={tabItems}
            size="small"
            type="editable-card"
            hideAdd
            onEdit={(key, action) => {
              if (action === "add") onTabAdd();
              else if (action === "remove" && typeof key === "string") onTabClose(key);
            }}
          />
        )}
      </div>

      <style>{`
        .query-input-panel {
          display: flex;
          flex-direction: column;
          height: 100%;
          background: #FFFFFF;
        }

        .editor-toolbar {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 6px 12px;
          background: #F5F5F7;
          border-bottom: 1px solid #E5E5EA;
        }

        .hint-text {
          font-size: 11px;
        }

        .editor-area {
          flex: 1;
          min-height: 0;
          display: flex;
          flex-direction: column;
        }

        .editor-area .ant-tabs {
          height: 100%;
          display: flex;
          flex-direction: column;
        }

        .editor-area .ant-tabs-nav {
          margin: 0;
          padding: 0 8px;
          background: #F5F5F7;
        }

        .editor-area .ant-tabs-content-holder {
          flex: 1;
          overflow: hidden;
        }

        .editor-area .ant-tabs-content {
          height: 100%;
        }

        .editor-area .ant-tabs-tabpane {
          height: 100%;
        }

        .tab-label {
          display: flex;
          align-items: center;
          gap: 4px;
        }

        .tab-name {
          max-width: 100px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .tab-dirty {
          color: #FF9500;
          font-weight: bold;
        }

        .tab-close {
          font-size: 10px;
          margin-left: 4px;
          opacity: 0.5;
        }

        .tab-close:hover {
          opacity: 1;
          color: #FF3B30;
        }

        .editor-container {
          height: 100%;
        }

        .empty-editor {
          display: flex;
          justify-content: center;
          align-items: center;
          height: 100%;
          background: #F5F5F7;
        }
      `}</style>
    </div>
  );
}
