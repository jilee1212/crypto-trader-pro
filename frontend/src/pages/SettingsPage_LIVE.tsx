/**
 * Settings page component - LIVE TRADING ONLY
 */

import React, { useState } from 'react';
import {
  Card,
  Form,
  Input,
  Button,
  Alert,
  Typography,
  Space,
  Divider,
  message,
  Row,
  Col,
  Statistic,
  Tag
} from 'antd';
import {
  KeyOutlined,
  SafetyOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ApiOutlined,
  WarningOutlined
} from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { binanceApi, ApiKeysRequest } from '../services/binanceApi';
import { useAuthStore } from '../stores/authStore';

const { Title, Text, Paragraph } = Typography;

interface ApiSettingsFormData {
  api_key: string;
  api_secret: string;
  // testnet removed - LIVE TRADING ONLY
}

export const SettingsPage: React.FC = () => {
  const [form] = Form.useForm<ApiSettingsFormData>();
  const [showApiSecret, setShowApiSecret] = useState(false);
  const { user } = useAuthStore();
  const queryClient = useQueryClient();

  // Test API connection
  const { data: connectionStatus, refetch: testConnection, isLoading: testingConnection } = useQuery({
    queryKey: ['api-connection-test'],
    queryFn: () => binanceApi.testConnection(),
    enabled: false,
  });

  // Configure API keys mutation
  const configureApiMutation = useMutation({
    mutationFn: (data: ApiKeysRequest) => binanceApi.configureApiKeys(data),
    onSuccess: () => {
      message.success('LIVE API keys configured successfully!');
      queryClient.invalidateQueries({ queryKey: ['user-profile'] });
      testConnection();
    },
    onError: (error: any) => {
      message.error(`Failed to configure API keys: ${error.message}`);
    },
  });

  const handleSubmit = (values: ApiSettingsFormData) => {
    configureApiMutation.mutate({
      api_key: values.api_key,
      api_secret: values.api_secret,
      // testnet removed - always FALSE for live trading
    });
  };

  return (
    <div className="p-6">
      <Title level={2}>
        <ApiOutlined /> LIVE Trading Settings
      </Title>

      {/* LIVE TRADING WARNING */}
      <Alert
        message="⚠️ LIVE TRADING MODE ACTIVE"
        description="This system connects to LIVE Binance trading with REAL MONEY. All trades will be executed with actual funds."
        type="error"
        icon={<WarningOutlined />}
        showIcon
        style={{ marginBottom: 24, fontWeight: '500' }}
      />

      <Row gutter={[24, 24]}>
        {/* API Configuration */}
        <Col span={24} lg={16}>
          <Card title={<><KeyOutlined /> LIVE API Configuration</>}>
            {/* Connection Status */}
            {user?.binance_api_key && (
              <Alert
                message="API Connection Status"
                description={
                  connectionStatus?.success
                    ? `Connected to LIVE Binance. Trading: ${connectionStatus.can_trade ? 'Enabled' : 'Disabled'}`
                    : connectionStatus?.error || 'Not tested yet'
                }
                type={connectionStatus?.success ? 'success' : 'warning'}
                style={{ marginBottom: 16 }}
                action={
                  <Button size="small" onClick={() => testConnection()} loading={testingConnection}>
                    Test Connection
                  </Button>
                }
              />
            )}

            <Form
              form={form}
              layout="vertical"
              onFinish={handleSubmit}
              initialValues={{
                api_key: '',
                api_secret: '',
                // no testnet field
              }}
            >
              <Form.Item
                label={<><KeyOutlined /> LIVE API Key</>}
                name="api_key"
                rules={[
                  { required: true, message: 'Please enter your LIVE Binance API key' },
                  { min: 10, message: 'API key must be at least 10 characters' }
                ]}
              >
                <Input.Password
                  placeholder="Enter your LIVE Binance API key"
                  visibilityToggle
                />
              </Form.Item>

              <Form.Item
                label={<><SafetyOutlined /> LIVE API Secret</>}
                name="api_secret"
                rules={[
                  { required: true, message: 'Please enter your LIVE Binance API secret' },
                  { min: 10, message: 'API secret must be at least 10 characters' }
                ]}
              >
                <Input.Password
                  placeholder="Enter your LIVE Binance API secret"
                  visibilityToggle={{
                    visible: showApiSecret,
                    onVisibleChange: setShowApiSecret
                  }}
                />
              </Form.Item>

              {/* Removed testnet switch - LIVE TRADING ONLY */}

              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={configureApiMutation.isPending}
                  icon={<CheckCircleOutlined />}
                  danger
                  size="large"
                >
                  Configure LIVE Trading API Keys
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </Col>

        {/* Account Status */}
        <Col span={24} lg={8}>
          <Card title={<><SafetyOutlined /> Account Status</>}>
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              <Statistic
                title="Trading Mode"
                value="LIVE TRADING"
                valueStyle={{ color: '#cf1322' }}
                prefix={<WarningOutlined />}
              />

              <Tag color="red" style={{ padding: '8px 16px', fontSize: '14px', fontWeight: 'bold' }}>
                🔴 REAL MONEY TRADING
              </Tag>

              {connectionStatus?.success && (
                <div>
                  <Text strong>Connection Status:</Text>
                  <div style={{ marginTop: 8 }}>
                    <Tag color="green" icon={<CheckCircleOutlined />}>CONNECTED</Tag>
                  </div>
                  <div style={{ marginTop: 8 }}>
                    <Text type="secondary">
                      Trading: {connectionStatus.can_trade ? '✅ Enabled' : '❌ Disabled'}
                    </Text>
                  </div>
                </div>
              )}
            </Space>
          </Card>

          {/* LIVE Trading Instructions */}
          <Card
            title={<><ExclamationCircleOutlined /> LIVE API Setup</>}
            style={{ marginTop: 16 }}
            size="small"
          >
            <Paragraph>
              <Text strong>To get your LIVE Binance API keys:</Text>
            </Paragraph>
            <ol style={{ paddingLeft: 16 }}>
              <li>Go to <a href="https://www.binance.com/en/my/settings/api-management" target="_blank" rel="noopener noreferrer">Binance API Management</a></li>
              <li>Create a new API key with trading permissions</li>
              <li>Enable "Spot & Margin Trading" and "Futures Trading"</li>
              <li>Set IP restrictions for security</li>
              <li>Copy the API Key and Secret here</li>
            </ol>

            <Divider />

            <Alert
              message="Security Best Practices"
              description={
                <ul style={{ margin: 0, paddingLeft: 16 }}>
                  <li>Never share your API keys</li>
                  <li>Set IP restrictions on Binance</li>
                  <li>Only enable required permissions</li>
                  <li>Monitor your account regularly</li>
                  <li>This is LIVE trading with real money</li>
                </ul>
              }
              type="warning"
              showIcon
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};