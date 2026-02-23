/** Database form modal component */
import { useState } from "react";
import { Button, Form, Input, Modal, Space, message } from "antd";

import { apiService } from "../services/api";

interface DatabaseFormProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function DatabaseForm({ open, onClose, onSuccess }: DatabaseFormProps) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (values: { name: string; url: string }) => {
    setLoading(true);
    try {
      await apiService.createDatabase(values.name, values.url);
      message.success("Database added successfully");
      form.resetFields();
      onSuccess();
      onClose();
    } catch (error) {
      message.error(`Failed to add database: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title="Add Database Connection"
      open={open}
      onCancel={onClose}
      footer={null}
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{ url: "postgres://" }}
      >
        <Form.Item
          label="Connection Name"
          name="name"
          rules={[
            { required: true, message: "Please enter a name" },
            { max: 50, message: "Name must be less than 50 characters" },
          ]}
        >
          <Input placeholder="my-database" />
        </Form.Item>

        <Form.Item
          label="Connection URL"
          name="url"
          rules={[
            { required: true, message: "Please enter a connection URL" },
            {
              pattern: /^postgres:\/\/.+/,
              message: "URL must start with postgres://",
            },
          ]}
        >
          <Input placeholder="postgres://user:password@host:port/database" />
        </Form.Item>

        <Form.Item>
          <Space>
            <Button type="primary" htmlType="submit" loading={loading}>
              Connect
            </Button>
            <Button onClick={onClose}>Cancel</Button>
          </Space>
        </Form.Item>
      </Form>
    </Modal>
  );
}
