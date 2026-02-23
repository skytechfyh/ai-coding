/**
 * Query Result Table - DataGrip-style enhanced
 * Supports sorting, column resize, copy on click, data type indicators
 */
import { useState } from "react";
import { Button, Empty, Space, Table, Tag, Tooltip, Typography, message } from "antd";
import {
  DownloadOutlined,
  CheckOutlined,
  DatabaseOutlined,
} from "@ant-design/icons";
import type { ColumnsType, TablePaginationConfig } from "antd/es/table";
import type { FilterValue, SorterResult } from "antd/es/table/interface";

import type { QueryResult } from "../types";
import { colors } from "../styles/theme";

const { Text } = Typography;

interface ResultTableProps {
  result: QueryResult | null;
  sqlQuery?: string;
  databaseName?: string;
}

export function ResultTable({ result, sqlQuery, databaseName }: ResultTableProps) {
  const [copiedCell, setCopiedCell] = useState<string | null>(null);
  const [sortedInfo, setSortedInfo] = useState<SorterResult<Record<string, unknown>>>({});

  const handleCopyCell = (value: unknown) => {
    const text = value === null ? "NULL" : String(value);
    navigator.clipboard.writeText(text).then(() => {
      setCopiedCell(text);
      message.success("Copied to clipboard");
      setTimeout(() => setCopiedCell(null), 2000);
    });
  };

  const handleExport = async (format: "csv" | "json") => {
    if (!sqlQuery || !databaseName) {
      return;
    }

    try {
      const response = await fetch(
        `/api/v1/dbs/${databaseName}/export/${format}?sql=${encodeURIComponent(sqlQuery)}`
      );
      const data = await response.json();

      if (data.success) {
        const content = format === "csv" ? data.data.csv : data.data.json;
        const blob = new Blob([content], {
          type: format === "csv" ? "text/csv" : "application/json",
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `query_result.${format}`;
        a.click();
        URL.revokeObjectURL(url);
        message.success(`Exported as ${format.toUpperCase()}`);
      }
    } catch (error) {
      message.error("Export failed");
    }
  };

  const handleTableChange = (
    _pagination: TablePaginationConfig,
    _filters: Record<string, FilterValue | null>,
    sorter: SorterResult<Record<string, unknown>> | SorterResult<Record<string, unknown>>[]
  ) => {
    if (!Array.isArray(sorter)) {
      setSortedInfo(sorter);
    }
  };

  if (!result) {
    return (
      <div className="results-panel">
        <div className="results-header">
          <Text className="results-title">
            <DatabaseOutlined /> Results
          </Text>
        </div>
        <div className="results-empty">
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="Execute a query to see results"
          />
        </div>
      </div>
    );
  }

  const columns: ColumnsType<Record<string, unknown>> = result.columns.map((col) => ({
    title: (
      <div className="column-header">
        <span className="column-name">{col}</span>
      </div>
    ),
    dataIndex: col,
    key: col,
    sorter: true,
    sortOrder: sortedInfo.columnKey === col ? sortedInfo.order : undefined,
    ellipsis: true,
    render: (value: unknown) => {
      const isNull = value === null;
      const isCopied = copiedCell === (value === null ? "NULL" : String(value));

      return (
        <Tooltip title={isNull ? "NULL" : String(value)}>
          <div
            className={`cell-content ${isNull ? "null" : ""}`}
            onClick={() => handleCopyCell(value)}
          >
            {isCopied ? (
              <CheckOutlined style={{ color: colors.status.success }} />
            ) : isNull ? (
              <Text type="secondary" className="null-text">
                NULL
              </Text>
            ) : (
              <Text className="cell-value">{String(value)}</Text>
            )}
          </div>
        </Tooltip>
      );
    },
  }));

  return (
    <div className="results-panel">
      {/* Header */}
      <div className="results-header">
        <Text className="results-title">
          <DatabaseOutlined /> Results
        </Text>
        <Space>
          <Tag color="blue">{result.totalRows} rows</Tag>
          <Tag>{result.queryTime.toFixed(3)}s</Tag>
          {sqlQuery && databaseName && (
            <>
              <Button
                size="small"
                icon={<DownloadOutlined />}
                onClick={() => handleExport("csv")}
              >
                CSV
              </Button>
              <Button
                size="small"
                icon={<DownloadOutlined />}
                onClick={() => handleExport("json")}
              >
                JSON
              </Button>
            </>
          )}
        </Space>
      </div>

      {/* Table */}
      <div className="results-table">
        <Table
          columns={columns}
          dataSource={result.rows.map((row, idx) => ({ key: idx, ...row }))}
          rowKey="key"
          pagination={{
            pageSize: 100,
            showSizeChanger: true,
            pageSizeOptions: ["50", "100", "200", "500"],
            showTotal: (total, range) => `${range[0]}-${range[1]} of ${total}`,
          }}
          scroll={{ x: "max-content", y: "calc(100vh - 400px)" }}
          size="small"
          onChange={handleTableChange}
          showSorterTooltip={false}
        />
      </div>

      <style>{`
        .results-panel {
          display: flex;
          flex-direction: column;
          height: 100%;
          background: #FFFFFF;
        }

        .results-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 8px 12px;
          background: #F5F5F7;
          border-bottom: 1px solid #E5E5EA;
        }

        .results-title {
          font-weight: 600;
          font-size: 13px;
          color: #1D1D1F;
        }

        .results-empty {
          flex: 1;
          display: flex;
          justify-content: center;
          align-items: center;
          background: #F5F5F7;
        }

        .results-table {
          flex: 1;
          overflow: auto;
        }

        .column-header {
          display: flex;
          align-items: center;
          gap: 4px;
        }

        .column-name {
          font-weight: 600;
          font-size: 12px;
        }

        .cell-content {
          cursor: pointer;
          padding: 2px 4px;
          border-radius: 2px;
          transition: background 150ms ease;
          min-height: 20px;
        }

        .cell-content:hover {
          background: rgba(0, 122, 255, 0.08);
        }

        .cell-content.null {
          font-style: italic;
        }

        .null-text {
          font-style: italic;
        }

        .cell-value {
          font-family: "SF Mono", Monaco, Menlo, Consolas, monospace;
          font-size: 12px;
        }

        /* Table enhancements */
        .ant-table-thead > tr > th {
          background: #F5F5F7 !important;
          font-weight: 600;
          font-size: 12px;
          padding: 8px 12px !important;
        }

        .ant-table-tbody > tr > td {
          padding: 4px 12px !important;
          font-size: 12px;
        }

        .ant-table-tbody > tr:hover > td {
          background: rgba(0, 122, 255, 0.04) !important;
        }

        .ant-table-column-sorter {
          font-size: 10px;
        }
      `}</style>
    </div>
  );
}
