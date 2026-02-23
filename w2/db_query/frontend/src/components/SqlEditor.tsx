/** SQL Editor component with Monaco */
import { useRef } from "react";
import { Button, Space, Typography } from "antd";

import Editor, { OnMount } from "@monaco-editor/react";

const { Text } = Typography;

interface SqlEditorProps {
  value: string;
  onChange: (value: string) => void;
  onExecute: () => void;
  loading?: boolean;
}

export function SqlEditor({ value, onChange, onExecute, loading }: SqlEditorProps) {
  const editorRef = useRef<unknown>(null);

  const handleEditorMount: OnMount = (editor) => {
    editorRef.current = editor;
    // Add keyboard shortcut for Ctrl+Enter / Cmd+Enter
    editor.addCommand(
      // Ctrl+Enter or Cmd+Enter
      2048 | 3, // Monaco.KeyMod.CtrlCmd | Monaco.KeyCode.Enter
      () => {
        onExecute();
      }
    );
  };

  return (
    <div>
      <Space style={{ marginBottom: 8 }}>
        <Button
          type="primary"
          onClick={onExecute}
          loading={loading}
          disabled={!value.trim()}
        >
          Execute (Ctrl+Enter)
        </Button>
        <Text type="secondary">Press Ctrl+Enter to execute</Text>
      </Space>
      <Editor
        height="200px"
        defaultLanguage="sql"
        value={value}
        onChange={(val) => onChange(val || "")}
        onMount={handleEditorMount}
        options={{
          minimap: { enabled: false },
          fontSize: 14,
          lineNumbers: "on",
          scrollBeyondLastLine: false,
          automaticLayout: true,
        }}
      />
    </div>
  );
}
