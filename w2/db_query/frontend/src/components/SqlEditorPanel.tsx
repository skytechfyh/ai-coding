/**
 * SQL Editor Panel with Tabs - DataGrip-style
 * Supports multiple query tabs with Monaco Editor, IntelliSense, and keyboard shortcuts
 */
import { useRef, useEffect } from "react";
import { Button, Empty, Space, Tabs } from "antd";
import { PlayCircleOutlined, PlusOutlined, CloseOutlined } from "@ant-design/icons";
import Editor from "@monaco-editor/react";
import type { editor } from "monaco-editor";

import { dataGripTheme, THEME_NAME } from "../styles/monaco-theme";
import { registerSqlCompletionProvider } from "../styles/sql-completion";
import type { QueryTab } from "../types";

interface SqlEditorPanelProps {
  tabs: QueryTab[];
  activeTabId: string;
  onTabChange: (tabId: string) => void;
  onTabAdd: () => void;
  onTabClose: (tabId: string) => void;
  onTabUpdate: (tabId: string, sql: string) => void;
  onExecute: (tabId: string) => void;
  executingTabId: string | null;
  databaseName: string | null;
}

export function SqlEditorPanel({
  tabs,
  activeTabId,
  onTabChange,
  onTabAdd,
  onTabClose,
  onTabUpdate,
  onExecute,
  executingTabId,
  databaseName,
}: SqlEditorPanelProps) {
  const editorRefs = useRef<Record<string, editor.IStandaloneCodeEditor>>({});
  const completionProviderRef = useRef<unknown>(null);

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
      // Ctrl+Enter or Cmd+Enter
      2048 | 3, // Monaco.KeyMod.CtrlCmd | Monaco.KeyCode.Enter
      () => {
        onExecute(tabId);
      }
    );

    // Focus the editor
    editorInstance.focus();
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
            insertSpaces: true,
            wordWrap: "on",
            renderWhitespace: "selection",
            folding: true,
            scrollbar: {
              verticalScrollbarSize: 8,
              horizontalScrollbarSize: 8,
            },
            padding: { top: 8, bottom: 8 },
            quickSuggestions: true,
            suggestOnTriggerCharacters: true,
            acceptSuggestionOnEnter: "on",
            tabCompletion: "on",
          }}
        />
      </div>
    ),
  }));

  return (
    <div className="sql-editor-panel">
      {/* Toolbar */}
      <div className="editor-toolbar">
        <Space>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={() => activeTabId && onExecute(activeTabId)}
            loading={executingTabId === activeTabId}
            disabled={!activeTab?.sql.trim() || !databaseName}
            size="small"
          >
            Run
          </Button>
        </Space>
        <Button
          type="text"
          icon={<PlusOutlined />}
          onClick={onTabAdd}
          size="small"
        />
      </div>

      {/* Tabs */}
      <div className="editor-tabs">
        {tabs.length === 0 ? (
          <div className="empty-editor">
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="No query tabs"
            >
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
              if (action === "add") {
                onTabAdd();
              } else if (action === "remove" && typeof key === "string") {
                onTabClose(key);
              }
            }}
          />
        )}
      </div>

      <style>{`
        .sql-editor-panel {
          display: flex;
          flex-direction: column;
          height: 100%;
          background: #FFFFFF;
        }

        .editor-toolbar {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 8px 12px;
          background: #F5F5F7;
          border-bottom: 1px solid #E5E5EA;
        }

        .shortcut-hint {
          font-size: 11px;
        }

        .editor-tabs {
          flex: 1;
          min-height: 0;
          overflow: hidden;
        }

        .editor-tabs .ant-tabs-nav {
          margin: 0;
          padding: 0 8px;
          background: #F5F5F7;
        }

        .editor-tabs .ant-tabs-tab {
          padding: 6px 12px;
          margin: 0;
          background: transparent;
          border: none;
          border-radius: 4px 4px 0 0;
        }

        .editor-tabs .ant-tabs-tab-active {
          background: #FFFFFF;
        }

        .editor-tabs .ant-tabs-content-holder {
          flex: 1;
          overflow: hidden;
        }

        .editor-tabs .ant-tabs-content {
          height: 100%;
        }

        .editor-tabs .ant-tabs-tabpane {
          height: 100%;
        }

        .editor-container {
          height: 100%;
        }

        .tab-label {
          display: flex;
          align-items: center;
          gap: 4px;
        }

        .tab-name {
          max-width: 120px;
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
          transition: opacity 150ms;
        }

        .tab-close:hover {
          opacity: 1;
          color: #FF3B30;
        }

        .editor-container {
          height: 100%;
          border: none;
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
