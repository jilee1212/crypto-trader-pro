/**
 * Login page component
 */

import React from 'react';
import { Card, Form, Input, Button, Alert, Typography, Space, Divider } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { LoginRequest } from '../../types/auth.types';
import { ROUTES, APP_CONFIG } from '../../utils/constants';

const { Title, Text } = Typography;

interface LocationState {
  from?: string;
}

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const { login, isLoading, error, clearError } = useAuthStore();

  // Get redirect path from location state
  const from = (location.state as LocationState)?.from || ROUTES.DASHBOARD;

  const onFinish = async (values: LoginRequest) => {
    try {
      clearError();
      await login(values);

      // Redirect to intended page or dashboard
      navigate(from, { replace: true });
    } catch (error) {
      // Error is handled by the store
      console.error('Login failed:', error);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <Title level={2} className="text-gray-900">
            {APP_CONFIG.APP_NAME}
          </Title>
          <Text className="text-gray-600">
            Sign in to your account
          </Text>
        </div>

        <Card className="shadow-lg">
          {error && (
            <Alert
              message="Login Failed"
              description={error}
              type="error"
              closable
              onClose={clearError}
              className="mb-4"
            />
          )}

          <Form
            name="login"
            onFinish={onFinish}
            autoComplete="off"
            size="large"
            layout="vertical"
          >
            <Form.Item
              label="Username"
              name="username"
              rules={[
                { required: true, message: 'Please input your username!' },
                { min: 3, message: 'Username must be at least 3 characters!' },
              ]}
            >
              <Input
                prefix={<UserOutlined />}
                placeholder="Enter your username"
                autoComplete="username"
              />
            </Form.Item>

            <Form.Item
              label="Password"
              name="password"
              rules={[
                { required: true, message: 'Please input your password!' },
                { min: 8, message: 'Password must be at least 8 characters!' },
              ]}
            >
              <Input.Password
                prefix={<LockOutlined />}
                placeholder="Enter your password"
                autoComplete="current-password"
              />
            </Form.Item>

            <Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                loading={isLoading}
                className="w-full"
                size="large"
              >
                Sign In
              </Button>
            </Form.Item>

            <Divider>Or</Divider>

            <div className="text-center">
              <Space direction="vertical" size="small">
                <Text>Don't have an account?</Text>
                <Link to={ROUTES.REGISTER}>
                  <Button type="link" className="p-0">
                    Sign up now
                  </Button>
                </Link>
              </Space>
            </div>
          </Form>
        </Card>

        <div className="text-center">
          <Text type="secondary" className="text-xs">
            © 2025 {APP_CONFIG.APP_NAME}. Built for educational purposes only.
          </Text>
        </div>
      </div>
    </div>
  );
};