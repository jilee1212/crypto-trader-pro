/**
 * Header component for main layout
 */

import React from 'react';
import { Layout, Typography, Space, Dropdown, Avatar, Button, Badge } from 'antd';
import {
  UserOutlined,
  LogoutOutlined,
  SettingOutlined,
  BellOutlined,
  MenuOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';
import { useAuthStore } from '../../stores/authStore';
import { APP_CONFIG } from '../../utils/constants';

const { Header: AntHeader } = Layout;
const { Title } = Typography;

interface HeaderProps {
  collapsed: boolean;
  onToggle: () => void;
}

export const Header: React.FC<HeaderProps> = ({ collapsed, onToggle }) => {
  const { user, logout } = useAuthStore();

  const userMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: 'Profile',
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: 'Settings',
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: 'Logout',
      onClick: logout,
    },
  ];

  return (
    <AntHeader
      style={{
        backgroundColor: '#fff',
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
        padding: '0 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: '64px',
        position: 'sticky',
        top: 0,
        zIndex: 200
      }}
    >
      {/* Left side */}
      <Space size="middle" style={{ display: 'flex', alignItems: 'center' }}>
        <Button
          type="text"
          icon={<MenuOutlined />}
          onClick={onToggle}
          style={{ display: window.innerWidth < 1024 ? 'inline-flex' : 'none' }}
        />

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              backgroundColor: '#1677ff',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            <span style={{ color: 'white', fontWeight: 'bold', fontSize: '14px' }}>CT</span>
          </div>

          <Title
            level={4}
            style={{
              margin: 0,
              color: '#262626',
              display: window.innerWidth >= 576 ? 'block' : 'none'
            }}
          >
            {APP_CONFIG.APP_NAME}
          </Title>
        </div>
      </Space>

      {/* Right side */}
      <Space size="middle" style={{ display: 'flex', alignItems: 'center' }}>
        {/* Notifications */}
        <Badge count={0} showZero={false}>
          <Button
            type="text"
            icon={<BellOutlined />}
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          />
        </Badge>

        {/* User menu */}
        <Dropdown
          menu={{ items: userMenuItems }}
          placement="bottomRight"
          trigger={['click']}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              cursor: 'pointer',
              padding: '4px 8px',
              borderRadius: '6px',
              transition: 'background-color 0.2s'
            }}
            onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#f5f5f5')}
            onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
          >
            <Avatar
              size="small"
              icon={<UserOutlined />}
              style={{ backgroundColor: '#1677ff' }}
            />
            <div
              style={{
                textAlign: 'right',
                display: window.innerWidth >= 576 ? 'block' : 'none'
              }}
            >
              <div style={{ fontSize: '14px', fontWeight: '500', color: '#262626' }}>
                {user?.full_name || user?.username}
              </div>
              <div style={{ fontSize: '12px', color: '#8c8c8c' }}>
                Mainnet {/* LIVE TRADING ONLY */}
              </div>
            </div>
          </div>
        </Dropdown>
      </Space>
    </AntHeader>
  );
};