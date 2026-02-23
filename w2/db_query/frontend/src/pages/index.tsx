/**
 * Main page component - DataGrip-style layout
 * Three-panel layout: sidebar (databases/tables), query editor, results
 */
import { useState, useCallback } from "react";
import { message, Space, Typography } from "antd";

import { DatabaseForm } from "../components/DatabaseForm";
import { DatabaseSidebar } from "../components/DatabaseSidebar";
import { QueryHistory } from "../components/QueryHistory";
import { QueryInputPanel } from "../components/QueryInputPanel";
import { ResultTable } from "../components/ResultTable";
import { MainLayout } from "../layouts/MainLayout";
import { apiService } from "../services/api";
import type { QueryResult, QueryTab } from "../types";

const { Title } = Typography;

// Generate unique IDs for tabs
const generateTabId = () => `tab-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;

const DEFAULT_TAB: QueryTab = {
  id: generateTabId(),
  name: "Query 1",
  sql: "",
  isDirty: false,
};

export function MainPage() {
  const [selectedDatabase, setSelectedDatabase] = useState<string | null>(null);
  const [queryResult, setQueryResult] = useState<QueryResult | null>(null);
  const [executingTabId, setExecutingTabId] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [historyKey, setHistoryKey] = useState(0);

  // Tabs state
  const [tabs, setTabs] = useState<QueryTab[]>([DEFAULT_TAB]);
  const [activeTabId, setActiveTabId] = useState<string>(DEFAULT_TAB.id);

  const handleSelectDatabase = async (name: string) => {
    setSelectedDatabase(name);
    // Clear results when switching databases
    setQueryResult(null);
  };

  const handleSelectTable = (tableName: string, _tableType: "table" | "view") => {
    // Generate a SELECT statement for the table
    const sql = `SELECT * FROM ${tableName} LIMIT 100`;
    const activeTab = tabs.find((t) => t.id === activeTabId);
    if (activeTab) {
      handleTabUpdate(activeTabId, sql);
    }
  };

  const handleExecuteQuery = async (tabId: string, sql?: string) => {
    const tab = tabs.find((t) => t.id === tabId);
    const querySql = sql || tab?.sql;
    if (!selectedDatabase || !querySql?.trim()) {
      return;
    }

    setExecutingTabId(tabId);
    try {
      const result = await apiService.executeQuery(selectedDatabase, querySql);
      setQueryResult(result);
      // Mark tab as not dirty after successful execution
      setTabs((prev) =>
        prev.map((t) => (t.id === tabId ? { ...t, isDirty: false } : t))
      );
      // Refresh history after query
      setHistoryKey((k) => k + 1);
    } catch (error) {
      message.error(`Query failed: ${error}`);
      setQueryResult(null);
    } finally {
      setExecutingTabId(null);
    }
  };

  const handleRefresh = () => {
    if (selectedDatabase) {
      handleSelectDatabase(selectedDatabase);
    }
  };

  const handleSelectFromHistory = (sql: string) => {
    const activeTab = tabs.find((t) => t.id === activeTabId);
    if (activeTab) {
      handleTabUpdate(activeTabId, sql);
    }
  };

  // Tab management
  const handleTabAdd = useCallback(() => {
    const newTab: QueryTab = {
      id: generateTabId(),
      name: `Query ${tabs.length + 1}`,
      sql: "",
      isDirty: false,
    };
    setTabs((prev) => [...prev, newTab]);
    setActiveTabId(newTab.id);
    setQueryResult(null);
  }, [tabs.length]);

  const handleTabClose = useCallback(
    (tabId: string) => {
      if (tabs.length === 1) {
        // Don't close the last tab, just clear it
        setTabs((prev) =>
          prev.map((t) => (t.id === tabId ? { ...t, sql: "", isDirty: false } : t))
        );
        setQueryResult(null);
        return;
      }

      setTabs((prev) => prev.filter((t) => t.id !== tabId));

      // If closing active tab, switch to first tab
      if (tabId === activeTabId) {
        const remainingTabs = tabs.filter((t) => t.id !== tabId);
        setActiveTabId(remainingTabs[0].id);
      }

      setQueryResult(null);
    },
    [tabs, activeTabId]
  );

  const handleTabUpdate = useCallback((tabId: string, sql: string) => {
    setTabs((prev) =>
      prev.map((t) =>
        t.id === tabId ? { ...t, sql, isDirty: sql !== t.sql } : t
      )
    );
  }, []);

  // Header component
  const header = (
    <Space>
      <Title level={4} style={{ margin: 0 }}>
        DB Query
      </Title>
      {selectedDatabase && (
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          Connected: {selectedDatabase}
        </Typography.Text>
      )}
    </Space>
  );

  // Sidebar component
  const sidebar = (
    <DatabaseSidebar
      selectedDatabase={selectedDatabase}
      onSelectDatabase={handleSelectDatabase}
      onSelectTable={handleSelectTable}
      onAddDatabase={() => setFormOpen(true)}
      onRefresh={handleRefresh}
    />
  );

  // Query panel - unified input for SQL and natural language
  const queryPanel = (
    <QueryInputPanel
      tabs={tabs}
      activeTabId={activeTabId}
      onTabChange={setActiveTabId}
      onTabAdd={handleTabAdd}
      onTabClose={handleTabClose}
      onTabUpdate={handleTabUpdate}
      onExecute={handleExecuteQuery}
      executingTabId={executingTabId}
      databaseName={selectedDatabase}
    />
  );

  // Results panel
  const resultsPanel = (
    <ResultTable
      result={queryResult}
      sqlQuery={tabs.find((t) => t.id === activeTabId)?.sql}
      databaseName={selectedDatabase ?? undefined}
    />
  );

  return (
    <>
      <MainLayout
        header={header}
        sidebar={sidebar}
        queryPanel={queryPanel}
        resultsPanel={resultsPanel}
      />

      {/* Database Form Modal */}
      <DatabaseForm
        open={formOpen}
        onClose={() => setFormOpen(false)}
        onSuccess={handleRefresh}
      />

      {/* Query History Drawer */}
      {selectedDatabase && (
        <QueryHistory
          key={historyKey}
          databaseName={selectedDatabase}
          onSelectQuery={handleSelectFromHistory}
        />
      )}

      <style>{`
        .ant-layout-sider-trigger {
          display: none;
        }
      `}</style>
    </>
  );
}
