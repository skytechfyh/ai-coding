/** Query history panel component */
import { useEffect, useState } from "react";
import { Card, List, Typography } from "antd";

const { Text } = Typography;

interface QueryHistoryProps {
  databaseName: string;
  onSelectQuery: (sql: string) => void;
}

interface QueryRecord {
  id: string;
  sql: string;
  executedAt: string;
  rowCount: number;
  duration: number;
  status: string;
}

export function QueryHistory({ databaseName, onSelectQuery }: QueryHistoryProps) {
  const [history, setHistory] = useState<QueryRecord[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (databaseName) {
      loadHistory();
    }
  }, [databaseName]);

  const loadHistory = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/dbs/${databaseName}/history`);
      const data = await response.json();
      if (data.success) {
        setHistory(data.data.history || []);
      }
    } catch (error) {
      console.error("Failed to load history:", error);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleString();
  };

  return (
    <Card title="Query History" loading={loading} size="small">
      <List
        size="small"
        dataSource={history}
        renderItem={(item) => (
          <List.Item
            style={{ cursor: "pointer" }}
            onClick={() => onSelectQuery(item.sql)}
          >
            <div style={{ width: "100%" }}>
              <Text code style={{ display: "block", marginBottom: 4 }}>
                {item.sql.length > 100 ? item.sql.substring(0, 100) + "..." : item.sql}
              </Text>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {formatDate(item.executedAt)} | {item.rowCount} rows |{" "}
                <Text type={item.status === "success" ? "success" : "danger"}>
                  {item.status}
                </Text>
              </Text>
            </div>
          </List.Item>
        )}
      />
      {history.length === 0 && !loading && (
        <Text type="secondary">No query history</Text>
      )}
    </Card>
  );
}
