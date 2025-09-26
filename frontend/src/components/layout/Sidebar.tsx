/**
 * Sidebar component for main layout
 */

import React from 'react';
import { Layout, Menu } from 'antd';
import {
  DashboardOutlined,
  StockOutlined,
  PieChartOutlined,
  BarChartOutlined,
  SettingOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';
import { useLocation, useNavigate } from 'react-router-dom';
import { ROUTES } from '../../utils/constants';

const { Sider } = Layout;

interface SidebarProps {
  collapsed: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({ collapsed }) => {
  const navigate = useNavigate();
  const location = useLocation();

  // Define menu items
  const menuItems: MenuProps['items'] = [
    {
      key: ROUTES.DASHBOARD,
      icon: <DashboardOutlined />,
      label: 'Dashboard',
      onClick: () => navigate(ROUTES.DASHBOARD),
    },
    {
      key: ROUTES.TRADING,
      icon: <StockOutlined />,
      label: 'Trading',
      onClick: () => navigate(ROUTES.TRADING),
    },
    {
      key: ROUTES.FUTURES,
      icon: <ThunderboltOutlined />,
      label: 'Futures',
      onClick: () => navigate(ROUTES.FUTURES),
    },
    {
      key: ROUTES.PORTFOLIO,
      icon: <PieChartOutlined />,
      label: 'Portfolio',
      onClick: () => navigate(ROUTES.PORTFOLIO),
    },
    {
      key: ROUTES.MARKET,
      icon: <BarChartOutlined />,
      label: 'Market',
      onClick: () => navigate(ROUTES.MARKET),
    },
    {
      type: 'divider',
    },
    {
      key: ROUTES.SETTINGS,
      icon: <SettingOutlined />,
      label: 'Settings',
      onClick: () => navigate(ROUTES.SETTINGS),
    },
  ];

  // Get current selected key from location
  const selectedKey = location.pathname;

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Menu */}
      <Menu
        mode="inline"
        selectedKeys={[selectedKey]}
        items={menuItems}
        style={{
          backgroundColor: 'transparent',
          border: 'none',
          flex: 1,
          paddingTop: '16px'
        }}
      />

      {/* Bottom info - LIVE TRADING WARNING */}
      {!collapsed && (
        <div style={{ padding: '16px', borderTop: '1px solid #f0f0f0' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '12px', color: '#999', marginBottom: '4px' }}>⚠️ Trading Mode</div>
            <div style={{
              display: 'inline-flex',
              alignItems: 'center',
              padding: '6px 12px',
              borderRadius: '12px',
              fontSize: '12px',
              fontWeight: 'bold',
              backgroundColor: '#fff2f0',
              color: '#cf1322',
              border: '1px solid #ffccc7'
            }}>
              🔴 LIVE TRADING
            </div>
            <div style={{ fontSize: '10px', color: '#cf1322', marginTop: '4px', fontWeight: '500' }}>
              Real Money Trading
            </div>
          </div>
        </div>
      )}
    </div>
  );
};