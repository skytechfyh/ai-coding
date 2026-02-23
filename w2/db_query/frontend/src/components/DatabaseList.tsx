/** Database list component */
import { useEffect, useState } from "react";
import { Button, Card, List, Modal, message } from "antd";

import { apiService } from "../services/api";
import type { DatabaseInfo } from "../types";

interface DatabaseListProps {
  selectedDatabase: string | null;
  onSelectDatabase: (name: string) => void;
  onRefresh: () => void;
}

export function DatabaseList({
  selectedDatabase,
  onSelectDatabase,
  onRefresh,
}: DatabaseListProps) {
  const [databases, setDatabases] = useState<DatabaseInfo[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadDatabases();
  }, []);

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

  const handleDelete = async (name: string) => {
    Modal.confirm({
      title: "Delete Database Connection",
      content: `Are you sure you want to delete "${name}"?`,
      onOk: async () => {
        try {
          await apiService.deleteDatabase(name);
          message.success("Database deleted");
          loadDatabases();
          onRefresh();
        } catch (error) {
          message.error(`Failed to delete database: ${error}`);
        }
      },
    });
  };

  return (
    <Card title="Database Connections" loading={loading}>
      <List
        dataSource={databases}
        renderItem={(db) => (
          <List.Item
            key={db.name}
            actions={[
              <Button
                type="link"
                key="select"
                onClick={() => onSelectDatabase(db.name)}
              >
                Select
              </Button>,
              <Button
                type="link"
                danger
                key="delete"
                onClick={() => handleDelete(db.name)}
              >
                Delete
              </Button>,
            ]}
          >
            <List.Item.Meta
              title={
                <span
                  style={{
                    fontWeight: selectedDatabase === db.name ? "bold" : "normal",
                  }}
                >
                  {db.name}
                </span>
              }
              description={`${db.databaseType} - ${db.lastUsedAt || "Never used"}`}
            />
          </List.Item>
        )}
      />
    </Card>
  );
}
