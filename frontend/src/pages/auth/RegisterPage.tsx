/**
 * Register page component
 */

import React from 'react';
import { Card, Form, Input, Button, Alert, Typography, Space, Divider, message } from 'antd';
import { UserOutlined, LockOutlined, MailOutlined, UserAddOutlined } from '@ant-design/icons';
import { Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { RegisterRequest } from '../../types/auth.types';
import { ROUTES, APP_CONFIG } from '../../utils/constants';

const { Title, Text } = Typography;

export const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const [form] = Form.useForm();

  const { register, isLoading, error, clearError } = useAuthStore();

  const onFinish = async (values: RegisterRequest) => {
    try {
      clearError();
      await register(values);

      message.success('Registration successful! Please log in to continue.');
      navigate(ROUTES.LOGIN);
    } catch (error) {
      // Error is handled by the store
      console.error('Registration failed:', error);
    }
  };

  const validateConfirmPassword = (_: any, value: string) => {
    if (!value || form.getFieldValue('password') === value) {
      return Promise.resolve();
    }
    return Promise.reject(new Error('The two passwords that you entered do not match!'));
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <Title level={2} className="text-gray-900">
            {APP_CONFIG.APP_NAME}
          </Title>
          <Text className="text-gray-600">
            Create your trading account
          </Text>
        </div>

        <Card className="shadow-lg">
          {error && (
            <Alert
              message="Registration Failed"
              description={error}
              type="error"
              closable
              onClose={clearError}
              className="mb-4"
            />
          )}

          <Form
            form={form}
            name="register"
            onFinish={onFinish}
            autoComplete="off"
            size="large"
            layout="vertical"
          >
            <Form.Item
              label="Email"
              name="email"
              rules={[
                { required: true, message: 'Please input your email!' },
                { type: 'email', message: 'Please enter a valid email address!' },
              ]}
            >
              <Input
                prefix={<MailOutlined />}
                placeholder="Enter your email"
                autoComplete="email"
              />
            </Form.Item>

            <Form.Item
              label="Username"
              name="username"
              rules={[
                { required: true, message: 'Please input your username!' },
                { min: 3, message: 'Username must be at least 3 characters!' },
                { max: 50, message: 'Username must be less than 50 characters!' },
                {
                  pattern: /^[a-zA-Z0-9_]+$/,
                  message: 'Username can only contain letters, numbers, and underscores!'
                },
              ]}
            >
              <Input
                prefix={<UserOutlined />}
                placeholder="Choose a username"
                autoComplete="username"
              />
            </Form.Item>

            <Form.Item
              label="Full Name (Optional)"
              name="full_name"
              rules={[
                { max: 100, message: 'Full name must be less than 100 characters!' },
              ]}
            >
              <Input
                prefix={<UserAddOutlined />}
                placeholder="Enter your full name"
                autoComplete="name"
              />
            </Form.Item>

            <Form.Item
              label="Password"
              name="password"
              rules={[
                { required: true, message: 'Please input your password!' },
                { min: 8, message: 'Password must be at least 8 characters!' },
                {
                  pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
                  message: 'Password must contain at least one lowercase letter, one uppercase letter, and one number!'
                },
              ]}
            >
              <Input.Password
                prefix={<LockOutlined />}
                placeholder="Create a strong password"
                autoComplete="new-password"
              />
            </Form.Item>

            <Form.Item
              label="Confirm Password"
              name="confirm_password"
              dependencies={['password']}
              rules={[
                { required: true, message: 'Please confirm your password!' },
                { validator: validateConfirmPassword },
              ]}
            >
              <Input.Password
                prefix={<LockOutlined />}
                placeholder="Confirm your password"
                autoComplete="new-password"
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
                Create Account
              </Button>
            </Form.Item>

            <Divider>Or</Divider>

            <div className="text-center">
              <Space direction="vertical" size="small">
                <Text>Already have an account?</Text>
                <Link to={ROUTES.LOGIN}>
                  <Button type="link" className="p-0">
                    Sign in here
                  </Button>
                </Link>
              </Space>
            </div>
          </Form>
        </Card>

        <div className="text-center">
          <Text type="secondary" className="text-xs">
            By creating an account, you agree to use this platform for educational purposes only.
          </Text>
        </div>
      </div>
    </div>
  );
};