/**
 * Database Sidebar Component - DataGrip-style
 * Shows database connections and their tables/views in a tree structure
 */
import { useEffect, useState } from "react";
import { Button, Empty, Spin, Tree, Typography, message } from "antd";
import {
  DatabaseOutlined,
  TableOutlined,
  EyeOutlined,
  ReloadOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import type { TreeDataNode } from "antd";

import { apiService } from "../services/api";
import type { DatabaseInfo, DatabaseWithMetadata } from "../types";

const { Text } = Typography;

interface DatabaseSidebarProps {
  selectedDatabase: string | null;
  onSelectDatabase: (name: string) => void;
  onSelectTable: (tableName: string, tableType: "table" | "view") => void;
  onAddDatabase: () => void;
  onRefresh: () => void;
}

interface DatabaseTreeNode extends TreeDataNode {
  databaseInfo?: DatabaseInfo;
  tableInfo?: {
    name: string;
    type: "table" | "view";
  };
}

export function DatabaseSidebar({
  selectedDatabase,
  onSelectDatabase,
  onSelectTable,
  onAddDatabase,
  onRefresh,
}: DatabaseSidebarProps) {
  const [databases, setDatabases] = useState<DatabaseInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [databaseMetadata, setDatabaseMetadata] = useState<Record<string, DatabaseWithMetadata>>({});
  const [expandedKeys, setExpandedKeys] = useState<string[]>([]);

  useEffect(() => {
    loadDatabases();
  }, []);

  // Auto-expand selected database and load its metadata
  useEffect(() => {
    if (selectedDatabase && !expandedKeys.includes(`db:${selectedDatabase}`)) {
      // Add the database to expanded keys
      setExpandedKeys((prev) => [...prev, `db:${selectedDatabase}`]);
    }
  }, [selectedDatabase]);

  useEffect(() => {
    // Load metadata when expanded keys change
    const loadMetadata = async () => {
      for (const key of expandedKeys) {
        const dbName = key.replace("db:", "");
        if (key.startsWith("db:") && !databaseMetadata[dbName]) {
          try {
            const metadata = await apiService.getDatabase(dbName);
            setDatabaseMetadata((prev) => ({
              ...prev,
              [dbName]: metadata,
            }));
          } catch (error) {
            console.error("Failed to load metadata:", error);
          }
        }
      }
    };
    loadMetadata();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [expandedKeys]);

  const loadDatabases = async () => {
    setLoading(true);
    try {
      const result = await apiService.listDatabases();
      setDatabases(result.databases);
    } catch (error) {
      message.error(`Failed to load databases: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  const handleExpand = (expandedKeys: unknown) => {
    setExpandedKeys(expandedKeys as string[]);
  };

  const handleSelect = (selectedKeys: unknown) => {
    const keys = selectedKeys as string[];
    if (keys.length === 0) return;
    const key = keys[0];

    if (key.startsWith("db:")) {
      // Selected a database
      const dbName = key.replace("db:", "");
      onSelectDatabase(dbName);
    } else if (key.startsWith("table:") || key.startsWith("view:")) {
      // Selected a table or view
      const [type, name] = key.split(":");
      onSelectTable(name, type as "table" | "view");
    }
  };

  const buildTreeData = (): DatabaseTreeNode[] => {
    return databases.map((db) => {
      const metadata = databaseMetadata[db.name];
      const children: DatabaseTreeNode[] = [];

      if (metadata?.tables) {
        // Add tables
        const tables = metadata.tables.filter((t) => t.type === "table");
        const views = metadata.tables.filter((t) => t.type === "view");

        // Add table nodes
        tables.forEach((table) => {
          children.push({
            key: `table:${table.name}`,
            title: (
              <span className="tree-node table-node">
                <TableOutlined className="node-icon table-icon" />
                <span>{table.name}</span>
              </span>
            ),
            isLeaf: true,
            tableInfo: { name: table.name, type: "table" },
          });
        });

        // Add view nodes
        views.forEach((view) => {
          children.push({
            key: `view:${view.name}`,
            title: (
              <span className="tree-node view-node">
                <EyeOutlined className="node-icon view-icon" />
                <span>{view.name}</span>
              </span>
            ),
            isLeaf: true,
            tableInfo: { name: view.name, type: "view" },
          });
        });
      }

      return {
        key: `db:${db.name}`,
        title: (
          <span className="tree-node database-node">
            <DatabaseOutlined className="node-icon database-icon" />
            <span className="database-name">{db.name}</span>
            <Text type="secondary" className="database-type">
              {db.databaseType}
            </Text>
          </span>
        ),
        children: children.length > 0 ? children : undefined,
        databaseInfo: db,
      };
    });
  };

  return (
    <div className="database-sidebar">
      <div className="sidebar-actions">
        <Button
          type="text"
          size="small"
          icon={<PlusOutlined />}
          onClick={onAddDatabase}
          title="Add Database"
        />
        <Button
          type="text"
          size="small"
          icon={<ReloadOutlined />}
          onClick={() => {
            loadDatabases();
            onRefresh();
          }}
          title="Refresh"
        />
      </div>

      <div className="sidebar-tree">
        {loading ? (
          <div className="loading-container">
            <Spin size="small" />
          </div>
        ) : databases.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="No databases"
            className="empty-state"
          />
        ) : (
          <Tree
            defaultExpandAll={false}
            expandedKeys={expandedKeys}
            onExpand={handleExpand}
            onSelect={handleSelect}
            treeData={buildTreeData()}
            selectedKeys={selectedDatabase ? [`db:${selectedDatabase}`] : []}
          />
        )}
      </div>

      <style>{`
        .database-sidebar {
          display: flex;
          flex-direction: column;
          height: 100%;
        }

        .sidebar-actions {
          display: flex;
          justify-content: flex-end;
          padding: 4px 8px;
          border-bottom: 1px solid #E5E5EA;
          gap: 4px;
        }

        .sidebar-actions .ant-btn {
          font-size: 12px;
        }

        .sidebar-tree {
          flex: 1;
          overflow: auto;
          padding: 4px;
        }

        .loading-container {
          display: flex;
          justify-content: center;
          padding: 24px;
        }

        .empty-state {
          padding: 16px 8px;
        }

        .empty-state .ant-empty-description {
          font-size: 11px;
          color: #A1A1A6;
        }

        .tree-node {
          display: flex;
          align-items: center;
          gap: 4px;
          font-size: 12px;
        }

        .node-icon {
          font-size: 11px;
        }

        .database-icon {
          color: #007AFF;
        }

        .table-icon {
          color: #34C759;
        }

        .view-icon {
          color: #5856D6;
        }

        .database-name {
          font-weight: 500;
        }

        .database-type {
          font-size: 9px;
          text-transform: uppercase;
          margin-left: auto;
          color: #A1A1A6;
        }

        .tree-node.table-node,
        .tree-node.view-node {
          padding: 1px 0;
        }

        .ant-tree .ant-tree-node-content-wrapper {
          padding: 0 2px !important;
        }

        .ant-tree .ant-tree-switcher {
          width: 16px !important;
          line-height: 18px !important;
        }

        .ant-tree .ant-tree-title {
          font-size: 12px !important;
        }
      `}</style>
    </div>
  );
}
