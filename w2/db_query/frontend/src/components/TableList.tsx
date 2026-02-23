/** Table list component */
import { useState } from "react";
import { Card, Input, List, Table, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";

import type { TableMetadata, Column } from "../types";

const { Text } = Typography;

interface TableListProps {
  tables: TableMetadata[];
}

export function TableList({ tables }: TableListProps) {
  const [searchText, setSearchText] = useState("");
  const [selectedTable, setSelectedTable] = useState<string | null>(null);

  const filteredTables = tables.filter((table) =>
    table.name.toLowerCase().includes(searchText.toLowerCase())
  );

  const columns: ColumnsType<Column> = [
    {
      title: "Column Name",
      dataIndex: "name",
      key: "name",
    },
    {
      title: "Data Type",
      dataIndex: "dataType",
      key: "dataType",
    },
    {
      title: "Nullable",
      dataIndex: "isNullable",
      key: "isNullable",
      render: (nullable: boolean) => (nullable ? "YES" : "NO"),
    },
    {
      title: "Primary Key",
      dataIndex: "isPrimaryKey",
      key: "isPrimaryKey",
      render: (pk: boolean) => (pk ? "YES" : "-"),
    },
  ];

  const selectedTableData = tables.find((t) => t.name === selectedTable);

  return (
    <Card
      title="Tables & Views"
      extra={
        <Input
          placeholder="Search tables..."
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          style={{ width: 200 }}
        />
      }
    >
      <List
        size="small"
        dataSource={filteredTables}
        style={{ maxHeight: 200, overflow: "auto" }}
        renderItem={(table) => (
          <List.Item
            key={table.name}
            onClick={() => setSelectedTable(table.name)}
            style={{
              cursor: "pointer",
              backgroundColor: selectedTable === table.name ? "#f0f0f0" : "white",
            }}
          >
            <Text>
              {table.name}{" "}
              <Text type="secondary">({table.type})</Text>
            </Text>
          </List.Item>
        )}
      />

      {selectedTableData && (
        <div style={{ marginTop: 16 }}>
          <Text strong>
            Columns for {selectedTableData.name}:
          </Text>
          <Table
            columns={columns}
            dataSource={selectedTableData.columns}
            rowKey="name"
            size="small"
            pagination={false}
          />
        </div>
      )}
    </Card>
  );
}
