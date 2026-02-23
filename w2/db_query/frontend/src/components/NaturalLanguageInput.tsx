/**
 * Natural Language Input Component - Apple Style
 * Allows users to describe queries in natural language
 */
import { useState } from "react";
import { Button, Input, message } from "antd";
import { ThunderboltOutlined, SendOutlined } from "@ant-design/icons";

import { apiService } from "../services/api";

const { TextArea } = Input;

interface NaturalLanguageInputProps {
  databaseName: string;
  onGenerateSql: (sql: string) => void;
  onExecuteQuery: () => void;
}

export function NaturalLanguageInput({
  databaseName,
  onGenerateSql,
  onExecuteQuery,
}: NaturalLanguageInputProps) {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);

  const handleGenerate = async () => {
    if (!prompt.trim()) {
      message.warning("Please enter a query description");
      return;
    }

    setLoading(true);
    try {
      const result = await apiService.generateSql(databaseName, prompt);
      onGenerateSql(result.sql);
      message.success("SQL generated, executing query...");

      // Auto-execute the generated SQL
      setTimeout(() => {
        onExecuteQuery();
      }, 100);
    } catch (error) {
      message.error(`Failed to generate SQL: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      handleGenerate();
    }
  };

  return (
    <div className="natural-language-input">
      <div className="nl-header">
        <ThunderboltOutlined className="nl-icon" />
        <span className="nl-title">AI SQL Generator</span>
      </div>
      <div className="nl-content">
        <TextArea
          placeholder="Describe query in natural language..."
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
          className="nl-textarea"
          autoSize
        />
        <Button
          type="primary"
          icon={<SendOutlined />}
          onClick={handleGenerate}
          loading={loading}
          size="small"
        >
          Generate
        </Button>
      </div>

      <style>{`
        .natural-language-input {
          background: #FFFFFF;
          border-bottom: 1px solid #E5E5EA;
          padding: 8px 12px;
        }

        .nl-header {
          display: flex;
          align-items: center;
          gap: 6px;
          margin-bottom: 6px;
        }

        .nl-icon {
          font-size: 12px;
          color: #007AFF;
        }

        .nl-title {
          font-size: 11px;
          font-weight: 600;
          color: #1D1D1F;
        }

        .nl-content {
          display: flex;
          gap: 8px;
          align-items: center;
        }

        .nl-textarea {
          flex: 1;
          border-radius: 4px;
          font-size: 12px;
        }

        .nl-textarea:focus {
          border-color: #007AFF;
          box-shadow: 0 0 0 2px rgba(0, 122, 255, 0.1);
        }
      `}</style>
    </div>
  );
}
